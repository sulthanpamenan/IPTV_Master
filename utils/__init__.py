import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

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
