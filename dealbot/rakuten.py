"""楽天ウェブサービス APIクライアント（2026年新仕様: applicationId + accessKey + Origin/Referer）"""
import json
import time
import urllib.error
import urllib.parse
import urllib.request

SEARCH_URL = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/{version}"
RANKING_URL = "https://openapi.rakuten.co.jp/ichibaranking/api/IchibaItem/Ranking/{version}"


def _force_ipv4():
    """自宅回線がIPv6の場合でも、楽天APIへはIPv4で接続する（許可IPをIPv4で登録するため）"""
    import socket
    if getattr(socket, "_dealbot_v4", False):
        return
    orig = socket.getaddrinfo

    def v4only(host, port, family=0, *args, **kw):
        return orig(host, port, socket.AF_INET, *args, **kw)
    socket.getaddrinfo = v4only
    socket._dealbot_v4 = True


class RakutenClient:
    def __init__(self, cfg):
        if cfg.get("force_ipv4", True):
            _force_ipv4()
        self.app_id = cfg["application_id"]
        self.access_key = cfg["access_key"]
        self.affiliate_id = cfg.get("affiliate_id", "")
        self.origin = cfg["origin"]  # アプリ登録時の「許可されたWebサイト」と同じURL
        self.search_ver = cfg.get("search_api_version", "20260701")
        self.ranking_ver = cfg.get("ranking_api_version", "20220601")
        self.interval = float(cfg.get("request_interval_sec", 1.6))
        self._last = 0.0

    def _get(self, url, params, retries=3):
        params = dict(params)
        params.update({
            "applicationId": self.app_id,
            "accessKey": self.access_key,
            "format": "json",
            "formatVersion": 2,
        })
        if self.affiliate_id:
            params["affiliateId"] = self.affiliate_id
        full = url + "?" + urllib.parse.urlencode(params)
        headers = {"Origin": self.origin, "Referer": self.origin + "/", "User-Agent": "dealbot/1.0"}
        for attempt in range(retries):
            wait = self.interval - (time.time() - self._last)
            if wait > 0:
                time.sleep(wait)
            self._last = time.time()
            try:
                req = urllib.request.Request(full, headers=headers)
                with urllib.request.urlopen(req, timeout=20) as res:
                    return json.loads(res.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    return {"items": [], "Items": []}
                if e.code in (429, 500, 503) and attempt < retries - 1:
                    time.sleep(5 * (attempt + 1))
                    continue
                body = e.read().decode("utf-8", "ignore")[:300]
                raise RuntimeError(f"楽天API エラー {e.code}: {body}") from None
            except (urllib.error.URLError, OSError) as e:
                # スリープ復帰直後などネットワーク未接続時は待って再試行
                if attempt < retries - 1:
                    time.sleep(30)
                    continue
                raise RuntimeError(f"ネットワークエラー: {e}") from None
        return {"items": []}

    @staticmethod
    def _items(data):
        # formatVersion=2 は items（Searchは Items の場合もあるため両対応）
        return data.get("items") or data.get("Items") or []

    def search(self, keyword, hits=10, sort="-reviewCount", **kw):
        p = {"keyword": keyword, "hits": hits, "sort": sort, "availability": 1}
        p.update(kw)
        return self._items(self._get(SEARCH_URL.format(version=self.search_ver), p))

    def item(self, item_code):
        items = self._items(self._get(SEARCH_URL.format(version=self.search_ver), {"itemCode": item_code}))
        return items[0] if items else None

    def ranking(self, genre_id=None, **kw):
        p = dict(kw)
        if genre_id:
            p["genreId"] = genre_id
        return self._items(self._get(RANKING_URL.format(version=self.ranking_ver), p))
