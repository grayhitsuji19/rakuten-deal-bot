"""楽天 買い時ボット CLI

使い方:
  python3 -m dealbot.main discover   # targets.json のキーワードから追跡商品を登録
  python3 -m dealbot.main daily      # 価格取得 → 判定 → 投稿文生成 → ページ生成（毎日1回）
  python3 -m dealbot.main post       # 当日の投稿文をXへ投稿（config の x.enabled=true 時のみ）
オプション: --mock（疑似API）  --date YYYY-MM-DD（テスト用の日付指定）
"""
import argparse
import datetime as dt
import json
import os
import sys

from . import analyze, db, posts, site

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_json(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as f:
        return json.load(f)


def client(cfg, args):
    if args.mock:
        from .mock import MockClient
        return MockClient(args.date)
    from .rakuten import RakutenClient
    return RakutenClient(cfg["rakuten"])


def cmd_discover(con, cfg, args):
    targets = load_json("targets.json")
    c = client(cfg, args)
    n = 0
    for t in targets:
        items = c.search(t["keyword"], hits=t.get("hits", 5), **t.get("params", {}))
        for it in items[: t.get("hits", 5)]:
            if it.get("reviewCount", 0) < cfg.get("min_review_count", 30):
                continue
            if "ふるさと納税" in it.get("itemName", ""):
                continue  # ふるさと納税は寄付のため価格比較の対象外
            db.upsert_item(con, it, t["category"], t["keyword"], args.date)
            db.save_price(con, it, args.date)
            n += 1
    con.commit()
    print(f"追跡商品を {n} 件登録/更新しました")


def cmd_collect(con, cfg, args):
    c = client(cfg, args)
    ok = ng = 0
    con.execute("UPDATE items SET active=0 WHERE name LIKE '%ふるさと納税%'")
    for row in db.active_items(con):
        try:
            it = c.item(row["item_code"])
        except RuntimeError as e:
            print(e, file=sys.stderr)
            ng += 1
            continue
        if not it:
            con.execute("UPDATE items SET active=0 WHERE item_code=?", (row["item_code"],))
            ng += 1
            continue
        db.save_price(con, it, args.date)
        ok += 1
    con.commit()
    print(f"価格取得: 成功 {ok} / 失敗・終了 {ng}")


def cmd_daily(con, cfg, args):
    cmd_collect(con, cfg, args)
    deals = analyze.find_deals(con, args.date, cfg)
    texts = posts.generate(con, deals, args.date, cfg)
    os.makedirs(os.path.join(ROOT, "out", "posts"), exist_ok=True)
    os.makedirs(os.path.join(ROOT, "docs"), exist_ok=True)
    with open(os.path.join(ROOT, "out", "posts", f"{args.date}.txt"), "w", encoding="utf-8") as f:
        f.write("\n\n-----\n\n".join(texts))
    site.build(con, deals, args.date, cfg, os.path.join(ROOT, "docs", "index.html"))
    print(f"買い時 {len(deals)} 件 / 投稿文 {len(texts)} 件 / ページ更新 docs/index.html")


def cmd_post(con, cfg, args):
    xcfg = cfg.get("x", {})
    rows = con.execute("SELECT rowid,* FROM posts WHERE date=? AND posted=0", (args.date,)).fetchall()
    if not xcfg.get("enabled"):
        print(f"X投稿は無効です（config.json の x.enabled）。未投稿 {len(rows)} 件は out/posts/{args.date}.txt を参照")
        return
    from . import xpost
    import time
    for r in rows:
        try:
            xpost.post(r["text"], xcfg)
            con.execute("UPDATE posts SET posted=1 WHERE rowid=?", (r["rowid"],))
            con.commit()
            print("投稿:", r["item_code"])
            time.sleep(int(xcfg.get("interval_sec", 600)))  # 連投を避ける
        except Exception as e:  # noqa
            print("投稿失敗:", e, file=sys.stderr)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("command", choices=["discover", "collect", "daily", "post"])
    p.add_argument("--mock", action="store_true")
    p.add_argument("--date", default=dt.date.today().isoformat())
    p.add_argument("--db", default=None)
    args = p.parse_args()
    cfg = load_json("config.json")
    db_path = args.db or os.path.join(ROOT, cfg.get("db_path", "data/prices.db"))
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    con = db.connect(db_path)
    {"discover": cmd_discover, "collect": cmd_collect, "daily": cmd_daily, "post": cmd_post}[args.command](con, cfg, args)


if __name__ == "__main__":
    main()
