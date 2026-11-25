import json
import os
import re
import threading
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

_CACHE_IO_LOCK = threading.Lock()


def create_robust_session(headers=None):
    session = requests.Session()
    session.verify = False
    retries = Retry(total=3, backoff_factor=1.0, status_forcelist=[500, 502, 503, 504], raise_on_status=False)
    adapter = HTTPAdapter(max_retries=retries, pool_connections=20, pool_maxsize=20)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    if headers:
        session.headers.update(headers)
    return session


def clean_xml_text(val):
    if not val:
        return ""
    val_str = str(val)
    cleaned = "".join(
        ch
        for ch in val_str
        if (
            ch in ("\t", "\n", "\r")
            or (0x20 <= ord(ch) <= 0xD7FF)
            or (0xE000 <= ord(ch) <= 0xFFFD)
            or (0x10000 <= ord(ch) <= 0x10FFFF)
        )
    )
    cleaned = cleaned.replace("\xa0", " ")
    cleaned = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", " ", cleaned).strip()
    return re.sub(r"\s+", " ", cleaned)


def clean_url_str(val):
    if not val:
        return ""
    url_str = clean_xml_text(val)
    if url_str.startswith("//"):
        url_str = "https:" + url_str
    return url_str if url_str.startswith(("http://", "https://")) else ""


def extract_icon_from_any(val):
    if not val:
        return ""
    if isinstance(val, str):
        return clean_url_str(val)
    if isinstance(val, list):
        for entry in val:
            found = extract_icon_from_any(entry)
            if found:
                return found
        return ""
    if isinstance(val, dict):
        for key in ["url", "contentUrl", "path", "src", "image_url", "thumbnail_url", "poster", "image", "thumbnail"]:
            if val.get(key):
                found = extract_icon_from_any(val.get(key))
                if found:
                    return found
    return ""


def load_json_cache(cache_path, max_age_seconds=None):
    with _CACHE_IO_LOCK:
        if not os.path.exists(cache_path):
            return None
        try:
            if max_age_seconds is not None:
                age = time.time() - os.path.getmtime(cache_path)
                if age > max_age_seconds:
                    return None
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None


def save_json_cache(cache_path, payload):
    with _CACHE_IO_LOCK:
        cache_dir = os.path.dirname(cache_path)
        if cache_dir:
            os.makedirs(cache_dir, exist_ok=True)
        tmp_path = f"{cache_path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, cache_path)


def authenticate_fls_guest(session=None):
    if not session:
        session = create_robust_session()

    auth_url = "https://api.gizmott.com/api/v1/account/authenticate"
    headers = {
        "accept": "application/json, text/plain, */*",
        "channelid": "516",
        "country_code": "ID",
        "crossorigin": "true",
        "dev_id": "5d01d64ac5b0026957052f0330129fc6",
        "device_type": "web",
        "ip": "103.150.218.78",
        "pubid": "50183",
        "uid": "7938114",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36"
    }
    try:
        response = session.get(auth_url, headers=headers, timeout=15)
        if response.status_code == 200:
            return response.json().get("token")
    except Exception:
        pass
    return None
