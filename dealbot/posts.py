"""投稿文の生成（X想定：重み付き280字以内、PR表記を冒頭）"""
import datetime as dt
import unicodedata

URL_WEIGHT = 23


def x_length(text, urls=()):
    n = 0
    for u in urls:
        text = text.replace(u, "")
        n += URL_WEIGHT
    for ch in text:
        n += 2 if unicodedata.east_asian_width(ch) in ("W", "F", "A") else 1
    return n


def short_name(name, limit=40):
    # 楽天の商品名は【】や送料無料表記が長いので削る
    import re
    s = re.sub(r"【[^】]*】|\[[^\]]*\]|＼[^／]*／|★|☆|◆", "", name)
    s = " ".join(s.split())
    return s if len(s) <= limit else s[:limit] + "…"


def build_text(deal, today, cfg):
    it = deal["item"]
    url = it["affiliate_url"]
    tag = cfg.get("hashtag", "#楽天 #一人暮らし")
    head = "【PR】"
    if "30日最安値" in deal["reasons"]:
        line2 = f"過去30日の最安値（中央値より-{deal['drop']}%）"
    else:
        line2 = "・".join(deal["reasons"])
    price_line = f"実質{deal['effective']:,}円（{deal['price']:,}円・P{deal['point_rate']}倍）"
    note = f"※{dt.date.fromisoformat(today).strftime('%-m/%-d')}時点。価格は変動します"
    for limit in (40, 30, 20, 14):
        text = "\n".join([head + short_name(it["name"], limit), price_line, line2, url, note, tag])
        if x_length(text, [url]) <= 280:
            return text
    return "\n".join([head + short_name(it["name"], 10), price_line, url, note])


def generate(con, deals, today, cfg):
    max_n = int(cfg.get("max_posts_per_day", 5))
    cooldown = int(cfg.get("repost_cooldown_days", 7))
    since = (dt.date.fromisoformat(today) - dt.timedelta(days=cooldown)).isoformat()
    out = []
    for d in deals:
        if len(out) >= max_n:
            break
        code = d["item"]["item_code"]
        recent = con.execute(
            "SELECT 1 FROM posts WHERE item_code=? AND date>=? AND date<?", (code, since, today)
        ).fetchone()
        if recent:
            continue
        text = build_text(d, today, cfg)
        con.execute("INSERT OR REPLACE INTO posts(item_code,date,kind,text) VALUES(?,?,?,?)",
                    (code, today, "x", text))
        out.append(text)
    con.commit()
    return out
