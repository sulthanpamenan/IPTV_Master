import sys
import os
import json
import xml.etree.ElementTree as ET
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import create_robust_session, clean_xml_text

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 14; Chromecast HD Build/UTTC.250917.004; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/146.0.7680.177 Mobile Safari/537.36",
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Origin": "https://pluto.tv",
    "Referer": "https://pluto.tv/us/watch/live-tv/",
    "apollo-require-preflight": "true",
    "x-apollo-operation-name": "ChannelsMany",
}

MIRROR_EPG_URL = "https://raw.githubusercontent.com/matthuisman/i.mjh.nz/master/PlutoTV/us.xml"

def format_xmltv_date(dt_str):
    if not dt_str or not isinstance(dt_str, str):
        return ""
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt.strftime("%Y%m%d%H%M%S +0000")
    except Exception:
        return ""

def fetch_graphql_channels():
    url = "https://pluto.tv/api/tn/video/graphql/"
    all_channels = []
    start = 0
    rows = 100
    session = create_robust_session(HEADERS)
    extensions_dict = {"tnPersistedDocumentHash": "a8c66dc403e590458bf86eff582a5541a7e1986d75ca7543ae2d6fd1e60b2b3a"}

    while True:
        try:
            variables_dict = {
                "params": {
                    "userRegistrationCountry": "US", "userState": "ANONYMOUS",
                    "packageCode": "NEW_FREE_PACKAGE", "userProfileType": "ADULT",
                    "billingVendor": "cbscomp", "dma": 501, "stationId": None,
                    "channelCategorySlug": None, "platformType": "Desktop",
                    "showListing": True, "hideChannelsWithoutListings": True,
                    "rows": rows, "numOfUpcomingListings": 10,
                    "filterLockedChannels": False, "start": start,
                }
            }
            params = {
                "extensions": json.dumps(extensions_dict),
                "variables": json.dumps(variables_dict),
                "operationName": "ChannelsMany",
            }
            res = session.get(url, params=params, timeout=20)
            if res.status_code == 200:
                data = res.json()
                channels = data.get("data", {}).get("channelsMany")
                if not channels or not isinstance(channels, list):
                    break
                all_channels.extend(channels)
                if len(channels) < rows:
                    break
                start += rows
            else:
                break
        except Exception:
            break
    return all_channels

def generate_pluto_epg():
    try:
        print("[*] Starting Pluto TV EPG generation process...")
        channels = fetch_graphql_channels()
        tv_elem = ET.Element("tv", {"generator-info-name": "PlutoTV EPG Generator"})
        p_count = 0

        if channels and isinstance(channels, list):
            for ch in channels:
                if not isinstance(ch, dict): continue
                ch_id = str(ch.get("id") or ch.get("_id") or "").strip()
                if not ch_id: continue

                ch_elem = ET.SubElement(tv_elem, "channel", id=ch_id)
                disp_name = ET.SubElement(ch_elem, "display-name")
                disp_name.text = clean_xml_text(ch.get("name", "Pluto Channel"))

                logo = ch.get("colorLogoPNG")
                if isinstance(logo, dict): logo = logo.get("path", "")
                elif not isinstance(logo, str): logo = ""
                if logo:
                    ET.SubElement(ch_elem, "icon", src=clean_xml_text(logo))

                for item in ch.get("listings", []):
                    if not isinstance(item, dict): continue
                    title_text = clean_xml_text(item.get("title", ""))
                    if not title_text: continue
                    desc_text = clean_xml_text(item.get("description") or f"Broadcast of {title_text}")
                    start_xml = format_xmltv_date(item.get("start", ""))
                    stop_xml = format_xmltv_date(item.get("stop", ""))

                    if start_xml and stop_xml:
                        prog_elem = ET.SubElement(tv_elem, "programme", {"start": start_xml, "stop": stop_xml, "channel": ch_id})
                        ET.SubElement(prog_elem, "title", lang="en").text = title_text
                        ET.SubElement(prog_elem, "desc", lang="en").text = desc_text
                        p_count += 1

        if p_count == 0:
            session = create_robust_session(HEADERS)
            res_mirror = session.get(MIRROR_EPG_URL, timeout=30)
            if res_mirror.status_code == 200:
                with open("epg.xml", "wb") as f:
                    f.write(res_mirror.content)
            return

        try: ET.indent(tv_elem, space="  ")
        except AttributeError: pass

        tree = ET.ElementTree(tv_elem)
        with open("epg.xml", "wb") as f:
            tree.write(f, encoding="utf-8", xml_declaration=True)
        print(f"[SUCCESS] Pluto TV `epg.xml` generated successfully with {p_count} programs.")
    except Exception as e:
        print(f"[ERROR] Pluto TV EPG generation error: {e}")

if __name__ == "__main__":
    generate_pluto_epg()
