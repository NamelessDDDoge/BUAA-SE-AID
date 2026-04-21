from hashlib import md5
import random

import requests
from django.conf import settings


def fanyi_text(query):
    if not query or query == "无":
        return query

    if not getattr(settings, "ENABLE_FANYI", False):
        return query

    appid = getattr(settings, "BAIDU_FANYI_APP_ID", "")
    appkey = getattr(settings, "BAIDU_FANYI_APP_KEY", "")
    if not appid or not appkey:
        return query

    endpoint = "http://api.fanyi.baidu.com"
    path = "/api/trans/vip/translate"
    url = endpoint + path

    def make_md5(value, encoding="utf-8"):
        return md5(value.encode(encoding)).hexdigest()

    salt = random.randint(32768, 65536)
    sign = make_md5(appid + query + str(salt) + appkey)
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    payload = {
        "appid": appid,
        "q": query,
        "from": "en",
        "to": "zh",
        "salt": salt,
        "sign": sign,
    }

    try:
        response = requests.post(url, params=payload, headers=headers, timeout=15)
        response.raise_for_status()
        result = response.json()
        translated = [item["dst"] for item in result.get("trans_result", [])]
        return "\n".join(translated) if translated else query
    except Exception:
        return query
