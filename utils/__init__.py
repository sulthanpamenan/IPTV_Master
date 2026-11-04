import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def create_robust_session(headers=None):
    session = requests.Session()
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
    return "".join(
        ch
        for ch in val_str
        if (
            ch in ("\t", "\n", "\r")
            or (0x20 <= ord(ch) <= 0xD7FF)
            or (0xE000 <= ord(ch) <= 0xFFFD)
            or (0x10000 <= ord(ch) <= 0x10FFFF)
        )
    ).strip()
