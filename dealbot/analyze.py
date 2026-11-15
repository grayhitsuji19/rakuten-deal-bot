"""お得判定：ポイント込み実質価格で過去30日と比較"""
import datetime as dt
import statistics

from . import db


def effective_price(price, point_rate):
    # 楽天ポイント: 1倍=1%として計算（SPU等の個人倍率は含めない）
    return price - int(price * point_rate / 100)


def find_deals(con, today, cfg):
    min_days = int(cfg.get("min_history_days", 7))
    drop_th = float(cfg.get("min_drop_percent", 5))
    point_th = int(cfg.get("min_point_rate", 5))
    since = (dt.date.fromisoformat(today) - dt.timedelta(days=30)).isoformat()
    deals = []
    for it in db.active_items(con):
        rows = db.history(con, it["item_code"], since)
        cur = [r for r in rows if r["date"] == today]
        if not cur or not cur[0]["availability"] or not cur[0]["price"]:
            continue
        cur = cur[0]
        past = [r for r in rows if r["date"] < today and r["price"]]
        eff = effective_price(cur["price"], cur["point_rate"])
        reasons, score, drop = [], 0.0, 0.0
        if len(past) >= min_days:
            effs = [effective_price(r["price"], r["point_rate"]) for r in past]
            low, med = min(effs), statistics.median(effs)
            drop = (med - eff) / med * 100 if med else 0
            if eff < low and drop >= drop_th:
                reasons.append("30日最安値")
                score += 20 + drop  # 最安値を優先（自前データの独自性が出るため）
        if cur["point_rate"] >= point_th:
            reasons.append(f"ポイント{cur['point_rate']}倍")
            score += cur["point_rate"]
        if reasons:
            deals.append({
                "item": dict(it), "price": cur["price"], "point_rate": cur["point_rate"],
                "effective": eff, "drop": round(drop, 1), "reasons": reasons, "score": score,
                "review_avg": cur["review_avg"], "review_count": cur["review_count"],
                "history_days": len(past),
            })
    deals.sort(key=lambda d: d["score"], reverse=True)
    return deals
