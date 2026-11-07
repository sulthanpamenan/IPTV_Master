import os
import time
import requests
import threading
from urllib.parse import urljoin, unquote
from flask import Flask, Response, request
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

CHANNELS = [
    # --- TV Category ---
    {"name": "TV3", "slug": "tv3-live", "group": "General", "logo": "https://raw.githubusercontent.com/sulthanpamenan/IPTV_Master/main/Logos/General/TV3.png", "type": "tv"},
    {"name": "Drama Sangat", "slug": "drama-sangat", "group": "Drama", "logo": "https://raw.githubusercontent.com/sulthanpamenan/IPTV_Master/main/Logos/Drama/Drama_Sangat.png", "type": "tv"},
    {"name": "DidikTV KPM", "slug": "didik-tv-live", "group": "Education", "logo": "https://raw.githubusercontent.com/sulthanpamenan/IPTV_Master/main/Logos/Education/DidikTVKPM.png", "type": "tv"},
    {"name": "FIFA+", "slug": "fifa-plus", "group": "Sports", "logo": "https://raw.githubusercontent.com/sulthanpamenan/IPTV_Master/main/Logos/Sports/FIFA+.png", "type": "tv"},
    {"name": "TV9", "slug": "tv9-malaysia", "group": "General", "logo": "https://raw.githubusercontent.com/sulthanpamenan/IPTV_Master/main/Logos/General/TV9_(Malaysia).png", "type": "tv"},
    {"name": "TV2", "slug": "tv2-live", "group": "General", "logo": "https://raw.githubusercontent.com/sulthanpamenan/IPTV_Master/main/Logos/General/RTM_TV2.png", "type": "tv"},
    {"name": "TV AlHijrah", "slug": "al-hijrah", "group": "Religious", "logo": "https://raw.githubusercontent.com/sulthanpamenan/IPTV_Master/main/Logos/Religious/TV_AlHijrah.png", "type": "tv"},
    {"name": "Sukan+", "slug": "sukan-rtm", "group": "Sports", "logo": "https://raw.githubusercontent.com/sulthanpamenan/IPTV_Master/main/Logos/Sports/Sukan%2B_RTM.png", "type": "tv"},
    {"name": "Bernama TV", "slug": "bernama", "group": "News + Opinion", "logo": "https://raw.githubusercontent.com/sulthanpamenan/IPTV_Master/main/Logos/News_+_Opinion/Bernama_TV.png", "type": "tv"},
    {"name": "Okey", "slug": "okey", "group": "General", "logo": "https://raw.githubusercontent.com/sulthanpamenan/IPTV_Master/main/Logos/General/Okey_RTM.png", "type": "tv"},
    {"name": "TV IKIM", "slug": "ikim-live", "group": "Religious", "logo": "https://raw.githubusercontent.com/sulthanpamenan/IPTV_Master/main/Logos/Religious/TV_IKIM.png", "type": "tv"},
    {"name": "8TV", "slug": "8-tv", "group": "General", "logo": "https://raw.githubusercontent.com/sulthanpamenan/IPTV_Master/main/Logos/General/8TV.png", "type": "tv"},
    {"name": "TV Sarawak", "slug": "tv-sarawak-live", "group": "Local", "logo": "https://raw.githubusercontent.com/sulthanpamenan/IPTV_Master/main/Logos/Local/TV_Sarawak.png", "type": "tv"},
    {"name": "MPL Malaysia", "slug": "mpl-malaysia", "group": "Live Events", "logo": "https://raw.githubusercontent.com/sulthanpamenan/IPTV_Master/main/Logos/Live_Events/MPL_Malaysia.png", "type": "tv"},
    {"name": "Free Movies", "slug": "free-movies", "group": "Movies", "logo": "https://raw.githubusercontent.com/sulthanpamenan/IPTV_Master/main/Logos/Movies/Free_Movies.png", "type": "tv"},
    {"name": "PPA Asia Tier Badges KL Cup", "slug": "ppa-kl-cup", "group": "Live Sports", "logo": "https://raw.githubusercontent.com/sulthanpamenan/IPTV_Master/main/Logos/Live_Sports/PPA_Asia_Tier_Badges_KL_Cup.png", "type": "tv"},
    {"name": "Siara TV", "slug": "siara-tv", "group": "Testing", "logo": "https://raw.githubusercontent.com/sulthanpamenan/IPTV_Master/main/Logos/Testing/Siara_TV.png", "type": "tv"},
    {"name": "MySports", "slug": "mysport", "group": "Sports", "logo": "https://raw.githubusercontent.com/sulthanpamenan/IPTV_Master/main/Logos/Sports/MySports.png", "type": "tv"},
    {"name": "USIMTV", "slug": "usim-tv", "group": "Education", "logo": "https://raw.githubusercontent.com/sulthanpamenan/IPTV_Master/main/Logos/Education/USIMTV.png", "type": "tv"},
    {"name": "Borneo TV", "slug": "borneo-tv", "group": "Local", "logo": "https://raw.githubusercontent.com/sulthanpamenan/IPTV_Master/main/Logos/Local/Borneo_TV.png", "type": "tv"},
    {"name": "ION", "slug": "ion-ncis", "group": "True Crime", "logo": "https://raw.githubusercontent.com/sulthanpamenan/IPTV_Master/main/Logos/True_Crime/ION.png", "type": "tv"},
    {"name": "BeIN Sports 1", "slug": "being-sports-1", "group": "Sports", "logo": "https://raw.githubusercontent.com/sulthanpamenan/IPTV_Master/main/Logos/Sports/beIN_Sports_1.png", "type": "tv"},

    # --- Radio Category ---
    {"name": "Manis FM", "slug": "manis-fm", "group": "Radio - Malaysia", "logo": "https://raw.githubusercontent.com/sulthanpamenan/IPTV_Master/main/Logos/Radio/Manis_FM.png", "type": "radio"},
    {"name": "Suria FM", "slug": "suria-fm", "group": "Radio - Malaysia", "logo": "https://raw.githubusercontent.com/sulthanpamenan/IPTV_Master/main/Logos/Radio/Suria_FM.png", "type": "radio"},
    {"name": "Fly FM", "slug": "fly-fm", "group": "Radio - Malaysia", "logo": "https://raw.githubusercontent.com/sulthanpamenan/IPTV_Master/main/Logos/Radio/Fly_FM.png", "type": "radio"},
    {"name": "Hot FM", "slug": "hot-fm", "group": "Radio - Malaysia", "logo": "https://raw.githubusercontent.com/sulthanpamenan/IPTV_Master/main/Logos/Radio/Hot_FM.png", "type": "radio"},
    {"name": "IKIM FM", "slug": "ikim-fm", "group": "Radio - Malaysia", "logo": "https://raw.githubusercontent.com/sulthanpamenan/IPTV_Master/main/Logos/Radio/IKIM_FM.png", "type": "radio"},
    {"name": "Molek FM", "slug": "molek-fm", "group": "Radio - Malaysia", "logo": "https://raw.githubusercontent.com/sulthanpamenan/IPTV_Master/main/Logos/Radio/Molek_FM.png", "type": "radio"},
    {"name": "Eight无限", "slug": "eight-fm", "group": "Radio - Malaysia", "logo": "https://raw.githubusercontent.com/sulthanpamenan/IPTV_Master/main/Logos/Radio/Eight无限.png", "type": "radio"},
    {"name": "Kool FM", "slug": "kool-fm", "group": "Radio - Malaysia", "logo": "https://raw.githubusercontent.com/sulthanpamenan/IPTV_Master/main/Logos/Radio/Kool_FM.png", "type": "radio"},
    {"name": "Bernama Radio", "slug": "bernama-radio", "group": "Radio - Malaysia", "logo": "https://raw.githubusercontent.com/sulthanpamenan/IPTV_Master/main/Logos/Radio/Bernama_Radio.png", "type": "radio"},
    {"name": "Best FM", "slug": "best-fm", "group": "Radio - Malaysia", "logo": "https://raw.githubusercontent.com/sulthanpamenan/IPTV_Master/main/Logos/Radio/Best_FM.png", "type": "radio"}
]

GIST_ID = os.environ.get("GIST_ID")
GIST_RAW_URL = f"https://gist.githubusercontent.com/sulthanpamenan/{GIST_ID}/raw/malaysia_tv.json"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36"
ORIGIN_VAL = "https://malaysia-tv.net"
REFERER_VAL = "https://malaysia-tv.net/"

_cache_store = {"data": {}, "expires_at": 0}
_is_updating = False

def background_update_tokens():
    global _cache_store, _is_updating
    try:
        res = requests.get(GIST_RAW_URL, timeout=6)
        if res.status_code == 200:
            new_data = res.json()
            if new_data:
                _cache_store["data"] = new_data
                _cache_store["expires_at"] = time.time() + 120
    except Exception:
        pass
    finally:
        _is_updating = False

def get_latest_tokens():
    global _cache_store, _is_updating
    current_time = time.time()
    
    if not _cache_store["data"]:
        try:
            res = requests.get(GIST_RAW_URL, timeout=6)
            if res.status_code == 200:
                _cache_store["data"] = res.json()
                _cache_store["expires_at"] = current_time + 120
        except Exception:
            pass
        return _cache_store["data"]

    if current_time >= _cache_store["expires_at"] and not _is_updating:
        _is_updating = True
        update_thread = threading.Thread(target=background_update_tokens)
        update_thread.daemon = True
        update_thread.start()

    return _cache_store["data"]

@app.route("/")
def index():
    return "Termux Local Proxy Malaysia TV Active!"

@app.route("/playlist.m3u")
def get_master_playlist():
    host_url = request.host
    lines = ["#EXTM3U"]
    for ch in CHANNELS:
        lines.append(f'#EXTINF:-1 tvg-id="" tvg-name="" tvg-logo="{ch["logo"]}" group-title="{ch["group"]}",{ch["name"]}')
        lines.append(f"http://{host_url}/live/{ch['slug']}")
    return Response("\n".join(lines) + "\n", mimetype="audio/x-mpegurl")

@app.route("/live/<slug>")
def stream_proxy(slug):
    raw_url = get_latest_tokens().get(slug, {}).get("url", "")
    m3u8_url = raw_url.split("|")[0] if "|" in raw_url else raw_url
    if not m3u8_url:
        return "Stream URL not found", 503

    headers = {"User-Agent": USER_AGENT, "Origin": ORIGIN_VAL, "Referer": REFERER_VAL}
    try:
        res = requests.get(m3u8_url, headers=headers, timeout=10)
        if res.status_code != 200:
            return f"Upstream error: {res.status_code}", res.status_code

        base_url = m3u8_url.rsplit("/", 1)[0] + "/"
        host_url = request.host
        new_lines = []
        for line in res.text.splitlines():
            if line.startswith("#") or not line.strip():
                new_lines.append(line)
            else:
                full_url = line if line.startswith("http") else urljoin(base_url, line)
                encoded_url = requests.utils.quote(full_url)
                new_lines.append(f"http://{host_url}/ts_proxy?slug={slug}&url={encoded_url}")
        return Response("\n".join(new_lines), content_type="application/vnd.apple.mpegurl")
    except Exception as e:
        return f"Proxy Error: {e}", 500

@app.route("/ts_proxy")
def ts_proxy():
    target_url = unquote(request.args.get("url", ""))
    slug = request.args.get("slug", "")
    if not target_url:
        return "Invalid URL", 400

    headers = {"User-Agent": USER_AGENT, "Origin": ORIGIN_VAL, "Referer": REFERER_VAL}
    host_url = request.host

    if ".m3u8" in target_url:
        try:
            res = requests.get(target_url, headers=headers, timeout=10)
            if res.status_code != 200:
                return f"Manifest Error: {res.status_code}", res.status_code

            base_url = target_url.rsplit("/", 1)[0] + "/"
            new_lines = []
            for line in res.text.splitlines():
                if line.startswith("#") or not line.strip():
                    new_lines.append(line)
                else:
                    full_url = line if line.startswith("http") else urljoin(base_url, line)
                    encoded_url = requests.utils.quote(full_url)
                    new_lines.append(f"http://{host_url}/ts_proxy?slug={slug}&url={encoded_url}")

            return Response("\n".join(new_lines), content_type="application/vnd.apple.mpegurl")
        except Exception as e:
            return f"Sub-manifest Error: {e}", 500

    try:
        res = requests.get(target_url, headers=headers, stream=True, timeout=15)
        return Response(res.iter_content(chunk_size=32768), content_type="video/MP2T")
    except Exception as e:
        return f"Segment Error: {e}", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, threaded=True)
