import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from playwright.sync_api import sync_playwright

CHANNELS = [
    # --- TV Category ---
    {"name": "TV3", "slug": "tv3-live", "group": "General", "logo": "https://raw.githubusercontent.com/sulthanpamenan/IPTV_Master/main/Logos/General/TV3.png", "type": "tv"},
    {"name": "Drama Sangat", "slug": "drama-sangat", "group": "Drama", "logo": "https://raw.githubusercontent.com/sulthanpamenan/IPTV_Master/main/Logos/Drama/Drama_Sangat.png", "type": "tv"},
    {"name": "DidikTV KPM", "slug": "didik-tv-live", "group": "Education", "logo": "https://raw.githubusercontent.com/sulthanpamenan/IPTV_Master/main/Logos/Education/DidikTV_KPM.png", "type": "tv"},
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

def get_stream_url(slug):
    target_url = f"https://malaysia-tv.net/{slug}/"
    stream_url = ""
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36"
        )
        
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
        return ch['slug'], url
    else:
        print(f"[{ch['name']}] -> Failed")
        return ch['slug'], None

def update_m3u():
    m3u_content = """<!--more-->
<html>
<head>
<meta charset="utf-8">
<meta http-equiv="X-UA-Compatible" content="IE=edge">
<meta name="viewport" content="width=device-width, initial-scale=1">
<script language="javascript">
window.location.replace("https://sulthanpamenan.github.io/IPTV_Master/malaysia-tv/");
</script>
</head></html>

<=================== PLAYLIST AUTOGENERATED BY SUTAN PAMENAN ===================>

#EXTM3U
"""
    
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36"
    headers_suffix = f"|User-Agent={user_agent}&Origin=https://malaysia-tv.net&Referer=https://malaysia-tv.net/"
    
    print(f"Processing total {len(CHANNELS)} items with Multi-threading...")
    
    results = {}
    with ThreadPoolExecutor(max_workers=9) as executor:
        future_to_channel = {executor.submit(process_single_channel, ch): ch for ch in CHANNELS}
        for future in as_completed(future_to_channel):
            slug, url = future.result()
            if url:
                results[slug] = url

    for ch in CHANNELS:
        slug = ch['slug']
        if slug in results:
            url = results[slug]
            group_title = ch.get("group", "Others")
            tv_logo = ch.get("logo", "")
            item_type = ch.get("type", "tv")
            
            if item_type == "radio":
                m3u_content += f'#EXTINF:-1 radio="true" tvg-country="MY" tvg-logo="{tv_logo}" group-title="{group_title}",{ch["name"]}\n'
                m3u_content += f'{url}\n'
            else:
                m3u_content += f'#EXTINF:-1 tvg-id="" tvg-name="" tvg-logo="{tv_logo}" group-title="{group_title}",{ch["name"]}\n'
                m3u_content += '#KODIPROP:inputstreamaddon=inputstream.adaptive\n'
                m3u_content += '#KODIPROP:inputstream.adaptive.manifest_type=hls\n'
                m3u_content += f'#KODIPROP:inputstream.adaptive.stream_headers=User-Agent={user_agent}&Origin=https://malaysia-tv.net&Referer=https://malaysia-tv.net/\n'
                m3u_content += f'{url}\n'

    with open("playlist.m3u", "w", encoding="utf-8") as f:
        f.write(m3u_content)
    print("The unified M3U playlist has been successfully updated and cleaned!")

if __name__ == "__main__":
    update_m3u()
