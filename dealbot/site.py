"""買い時一覧ページ（静的HTML）を生成"""
import datetime as dt
import html

from . import db
from .analyze import effective_price


def sparkline(values, w=120, h=32):
    if len(values) < 2:
        return ""
    lo, hi = min(values), max(values)
    rng = (hi - lo) or 1
    step = w / (len(values) - 1)
    pts = " ".join(f"{i*step:.1f},{h - 3 - (v - lo) / rng * (h - 6):.1f}" for i, v in enumerate(values))
    lx, ly = (len(values) - 1) * step, h - 3 - (values[-1] - lo) / rng * (h - 6)
    return (f'<svg class="spark" viewBox="0 0 {w} {h}" width="{w}" height="{h}" aria-hidden="true">'
            f'<polyline points="{pts}" fill="none" stroke="currentColor" stroke-width="1.5"/>'
            f'<circle cx="{lx:.1f}" cy="{ly:.1f}" r="2.5" fill="var(--accent)"/></svg>')


CSS = """
:root{--bg:#fafaf7;--fg:#1d1d1b;--muted:#6b6b66;--line:#e4e2dc;--accent:#bf2c2c;--card:#fff}
@media (prefers-color-scheme:dark){:root{--bg:#161615;--fg:#ecebe6;--muted:#9a9993;--line:#2c2b29;--accent:#ff6b5e;--card:#1f1f1d}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font-family:-apple-system,"Hiragino Sans","Noto Sans JP",sans-serif;line-height:1.6}
main{max-width:880px;margin:0 auto;padding:16px}
.pr{font-size:13px;border:1px solid var(--line);padding:6px 10px;border-radius:6px;background:var(--card)}
h1{font-size:22px;margin:16px 0 4px}h2{font-size:17px;margin:28px 0 8px;border-bottom:1px solid var(--line);padding-bottom:4px}
.meta{color:var(--muted);font-size:13px}
.card{display:flex;gap:12px;background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px;margin:8px 0;align-items:center}
.card img{width:72px;height:72px;object-fit:contain;flex:none}
.card a{color:inherit}.name{font-size:14px}.price{font-weight:700;font-size:16px}
.tag{display:inline-block;font-size:12px;color:var(--accent);border:1px solid var(--accent);border-radius:4px;padding:0 6px;margin-right:4px}
.spark{color:var(--muted);flex:none}
table{width:100%;border-collapse:collapse;font-size:13px}td,th{border-bottom:1px solid var(--line);padding:6px 4px;text-align:left;vertical-align:middle}
td.num{text-align:right;white-space:nowrap}
footer{margin:32px 0;color:var(--muted);font-size:12px}
@media (max-width:600px){.spark{display:none}}
"""


def build(con, deals, today, cfg, out_path):
    title = cfg.get("site_title", "一人暮らしの楽天 買い時ノート")
    since = (dt.date.fromisoformat(today) - dt.timedelta(days=30)).isoformat()
    e = html.escape
    parts = [f'<!doctype html><html lang="ja"><head><meta charset="utf-8">'
             f'<meta name="viewport" content="width=device-width,initial-scale=1">'
             f'<title>{e(title)}</title><style>{CSS}</style></head><body><main>',
             '<p class="pr">【PR】本ページは楽天アフィリエイトによるプロモーションを含みます。</p>',
             f'<h1>{e(title)}</h1>',
             f'<p class="meta">価格取得日：{today}／価格・ポイントは変動します。購入前に商品ページでご確認ください。'
             f'実質価格は「価格−通常ポイント」の目安です（SPU等の個人倍率は含みません）。</p>',
             '<h2>今日の買い時</h2>']
    if not deals:
        parts.append('<p class="meta">本日の該当なし（価格履歴の蓄積中です）。</p>')
    for d in deals[:20]:
        it = d["item"]
        effs = [effective_price(r["price"], r["point_rate"]) for r in db.history(con, it["item_code"], since) if r["price"]]
        img = (f'<a href="{e(it["affiliate_url"])}" rel="sponsored noopener" target="_blank">'
               f'<img src="{e(it["image_url"])}" alt="" loading="lazy"></a>') if it["image_url"] else ""
        tags = "".join(f'<span class="tag">{e(r)}</span>' for r in d["reasons"])
        parts.append(
            f'<div class="card">{img}'
            f'<div style="flex:1;min-width:0"><div>{tags}</div>'
            f'<a class="name" href="{e(it["affiliate_url"])}" rel="sponsored noopener" target="_blank">{e(it["name"][:80])}</a>'
            f'<div class="price">実質 {d["effective"]:,}円 <span class="meta">（{d["price"]:,}円・P{d["point_rate"]}倍）</span></div>'
            f'</div>{sparkline(effs)}</div>')
    parts.append('<h2>追跡中の商品</h2><table><tr><th>商品</th><th>カテゴリ</th><th class="num">実質価格</th><th class="num">30日最安</th></tr>')
    for it in db.active_items(con):
        rows = [r for r in db.history(con, it["item_code"], since) if r["price"]]
        if not rows:
            continue
        effs = [effective_price(r["price"], r["point_rate"]) for r in rows]
        parts.append(
            f'<tr><td><a href="{e(it["affiliate_url"])}" rel="sponsored noopener" target="_blank">{e(it["name"][:50])}</a></td>'
            f'<td>{e(it["category"] or "")}</td><td class="num">{effs[-1]:,}円</td><td class="num">{min(effs):,}円</td></tr>')
    parts.append('</table><footer>'
                 '<a href="https://webservice.rakuten.co.jp/" target="_blank">Supported by Rakuten Developers</a>'
                 '</footer></main></body></html>')
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("".join(parts))
