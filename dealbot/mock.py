"""テスト用の疑似楽天APIクライアント（日付ごとに価格・ポイントが変動）"""
import hashlib
import random


class MockClient:
    def __init__(self, today):
        self.today = today

    def _rng(self, *keys):
        h = hashlib.md5("|".join(map(str, keys)).encode()).hexdigest()
        return random.Random(int(h[:8], 16))

    def _make(self, code, name):
        base = self._rng(code).randint(800, 30000)
        r = self._rng(code, self.today)
        price = int(base * r.uniform(0.85, 1.05) // 10 * 10)
        return {
            "itemCode": code, "itemName": f"【送料無料】{name} 大容量 まとめ買い ★レビュー特典",
            "itemPrice": price, "pointRate": r.choice([1, 1, 1, 2, 3, 5, 10]),
            "itemUrl": f"https://item.rakuten.co.jp/{code.replace(':', '/')}/",
            "affiliateUrl": f"https://hb.afl.rakuten.co.jp/hgc/xxxx/?pc=https%3A%2F%2Fitem.rakuten.co.jp%2F{code.replace(':', '%2F')}",
            "shopName": "テストショップ", "availability": 1,
            "reviewCount": self._rng(code, "rc").randint(10, 5000),
            "reviewAverage": round(self._rng(code, "ra").uniform(3.5, 4.9), 2),
            "mediumImageUrls": [],
        }

    def search(self, keyword, hits=10, **kw):
        k = hashlib.md5(keyword.encode()).hexdigest()[:6]
        return [self._make(f"shop{i}:{k}-{i}", keyword) for i in range(hits)]

    def item(self, item_code):
        return self._make(item_code, item_code.split(":")[1])
