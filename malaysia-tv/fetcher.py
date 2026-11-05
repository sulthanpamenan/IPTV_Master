import os
import time
import json
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from playwright.sync_api import sync_playwright

GIST_ID = os.environ.get("GIST_ID", "6055fb9a0d9c3754edc6cf956cdbf762")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN") 
GIST_FILENAME = os.environ.get("GIST_FILENAME", "malaysia_tv.json")
GIST_API_URL = f"https://api.github.com/gists/{GIST_ID}"

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
    {"name": "PPA Asia Tier Badges KL Cup", "slug": "ppa-kl-cup", "group": "Live Sports", "logo": "https://raw.githubusercontent.com/sulthanpamenan/IPTV_Master/main/Logos/Live_Events/PPA_Asia_Tier_Badges_KL_Cup.png", "type": "tv"},
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

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36"
ORIGIN_VAL = "https://malaysia-tv.net"
REFERER_VAL = "https://malaysia-tv.net/"

def get_stream_url(slug):
    target_url = f"https://malaysia-tv.net/{slug}/"
    stream_url = ""
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        page = browser.new_page(user_agent=USER_AGENT)
        
        def handle_request(request):
            nonlocal stream_url
            url = request.url
            if ".m3u8" in url and not any(ext in url for ext in [".aac", ".ts", ".mp3", ".js", "player-init"]):
                if not stream_url or "streamer/" in url:
                    stream_url = url

        page.on("request", handle_request)
        
        try:
            page.goto(target_url, timeout=30000, wait_until="domcontentloaded")
            for _ in range(12):
                if stream_url:
                    break
                time.sleep(0.5)
        except Exception:
            pass
        finally:
            browser.close()
            
    return stream_url

def process_single_channel(ch):
    url = get_stream_url(ch['slug'])
    if url:
        print(f"[{ch['name']}] -> Success")
        piped_url = f"{url}|User-Agent={USER_AGENT}&Origin={ORIGIN_VAL}&Referer={REFERER_VAL}"
        return ch['slug'], piped_url
    else:
        print(f"[{ch['name']}] -> Failed")
        return ch['slug'], None

def save_gist_tokens(tokens):
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json"
    }
    payload = {
        "files": {
            GIST_FILENAME: {
                "content": json.dumps(tokens, indent=4)
            }
        }
    }
    res = requests.patch(GIST_API_URL, headers=headers, json=payload, timeout=10)
    res.raise_for_status()
    print("[✓] Malaysia TV tokens successfully updated to Gist!")

if __name__ == "__main__":
    print(f"Processing total {len(CHANNELS)} items with Multi-threading...")
    results = {}
    
    with ThreadPoolExecutor(max_workers=9) as executor:
        future_to_channel = {executor.submit(process_single_channel, ch): ch for ch in CHANNELS}
        for future in as_completed(future_to_channel):
            slug, piped_url = future.result()
            if piped_url:
                results[slug] = {"url": piped_url}

    if results:
        try:
            save_gist_tokens(results)
            with open("malaysia_tv.json", "w", encoding="utf-8") as f:
                json.dump(results, f, indent=4)
            print("[✓] The local file malaysia_tv.json has been successfully updated!")
        except Exception as e:
            print(f"[!] Failed to save token: {e}")
