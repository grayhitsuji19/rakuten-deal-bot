"""価格履歴DB（SQLite）"""
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
  item_code TEXT PRIMARY KEY,
  name TEXT, item_url TEXT, affiliate_url TEXT, shop_name TEXT,
  category TEXT, keyword TEXT, image_url TEXT,
  active INTEGER DEFAULT 1, added_at TEXT
);
CREATE TABLE IF NOT EXISTS prices (
  item_code TEXT, date TEXT,
  price INTEGER, point_rate INTEGER, availability INTEGER,
  review_count INTEGER, review_avg REAL,
  PRIMARY KEY (item_code, date)
);
CREATE TABLE IF NOT EXISTS posts (
  item_code TEXT, date TEXT, kind TEXT, text TEXT, posted INTEGER DEFAULT 0,
  PRIMARY KEY (item_code, date, kind)
);
"""


def connect(path):
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con


def upsert_item(con, it, category, keyword, today):
    img = ""
    imgs = it.get("mediumImageUrls") or []
    if imgs:
        img = imgs[0] if isinstance(imgs[0], str) else imgs[0].get("imageUrl", "")
    con.execute(
        """INSERT INTO items(item_code,name,item_url,affiliate_url,shop_name,category,keyword,image_url,added_at)
           VALUES(?,?,?,?,?,?,?,?,?)
           ON CONFLICT(item_code) DO UPDATE SET name=excluded.name, item_url=excluded.item_url,
             affiliate_url=excluded.affiliate_url, shop_name=excluded.shop_name, image_url=excluded.image_url""",
        (it["itemCode"], it.get("itemName", ""), it.get("itemUrl", ""), it.get("affiliateUrl") or it.get("itemUrl", ""),
         it.get("shopName", ""), category, keyword, img, today),
    )


def save_price(con, it, today):
    con.execute(
        """INSERT OR REPLACE INTO prices(item_code,date,price,point_rate,availability,review_count,review_avg)
           VALUES(?,?,?,?,?,?,?)""",
        (it["itemCode"], today, int(it.get("itemPrice") or 0), int(it.get("pointRate") or 1),
         int(it.get("availability") or 0), int(it.get("reviewCount") or 0), float(it.get("reviewAverage") or 0)),
    )


def active_items(con):
    return con.execute("SELECT * FROM items WHERE active=1 ORDER BY category, item_code").fetchall()


def history(con, item_code, since):
    return con.execute(
        "SELECT * FROM prices WHERE item_code=? AND date>=? ORDER BY date", (item_code, since)
    ).fetchall()
