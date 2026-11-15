"""X（旧Twitter）への投稿：API v2 / OAuth 1.0a（標準ライブラリのみ）
X APIは従量課金（2026年時点 1投稿 約$0.01、事前クレジット購入が必要）"""
import base64
import hashlib
import hmac
import json
import secrets
import time
import urllib.parse
import urllib.request

TWEET_URL = "https://api.x.com/2/tweets"


def _q(s):
    return urllib.parse.quote(str(s), safe="~")


def _auth_header(method, url, keys):
    oauth = {
        "oauth_consumer_key": keys["api_key"],
        "oauth_nonce": secrets.token_hex(16),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_token": keys["access_token"],
        "oauth_version": "1.0",
    }
    param_str = "&".join(f"{_q(k)}={_q(v)}" for k, v in sorted(oauth.items()))
    base = "&".join([method, _q(url), _q(param_str)])
    key = f"{_q(keys['api_secret'])}&{_q(keys['access_secret'])}"
    sig = base64.b64encode(hmac.new(key.encode(), base.encode(), hashlib.sha1).digest()).decode()
    oauth["oauth_signature"] = sig
    return "OAuth " + ", ".join(f'{_q(k)}="{_q(v)}"' for k, v in sorted(oauth.items()))


def post(text, keys):
    body = json.dumps({"text": text}).encode("utf-8")
    req = urllib.request.Request(TWEET_URL, data=body, method="POST", headers={
        "Authorization": _auth_header("POST", TWEET_URL, keys),
        "Content-Type": "application/json",
    })
    with urllib.request.urlopen(req, timeout=20) as res:
        return json.loads(res.read().decode("utf-8"))
