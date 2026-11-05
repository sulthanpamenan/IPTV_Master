import sys
import os
from datetime import datetime
try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None
import html

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import create_robust_session, authenticate_fls_guest

def parse_time_to_xmltv(time_str):
    if not time_str: return ""
    try:
        clean_str = time_str.strip().replace("Z", "")
        dt = datetime.fromisoformat(clean_str)
        if ZoneInfo:
            dt = dt.replace(tzinfo=ZoneInfo("Asia/Jakarta"))
            return dt.strftime("%Y%m%d%H%M%S %z").strip()
        else:
            return dt.strftime("%Y%m%d%H%M%S") + " +0700"
    except Exception:
        return time_str

def generate_epg():
    session = create_robust_session()
    token = os.getenv("GIZMOTT_ACCESS_TOKEN") or authenticate_fls_guest(session)
    if not token:
        token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJjaGVjayI6dHJ1ZSwicHViaWQiOiI1MDE4MyIsInVpZCI6Ijc5MzgxMTQiLCJjb3VudHJ5X2NvZGUiOiJJIDIsImRldmljZV90eXBlIjoid2ViIiwiaWF0IjoxNzkwNSExNDE1LCJleHAiOjE3OTgyODc0MTV9.3yF9I5p_Y7m2YZZ-bYQkTxkmzR_uFhCfPwVSALIDDdw"

    headers = {
        "accept": "application/json, text/plain, */*", "access-token": token,
        "pubid": "50183", "channelid": "516", "country_code": "ID",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36",
    }

    try:
        channels_map = {}
        list_res = session.get("https://api.gizmott.com/api/v1/fastchannel/list", headers=headers, timeout=15)
        if list_res.status_code == 200:
            for ch in list_res.json().get("data", []):
                ch_id = str(ch.get("channel_id") or ch.get("id") or "")
                ch_name = ch.get("show_name") or ch.get("channel_name") or ch.get("name")
                if ch_id and ch_name: channels_map[ch_id] = ch_name

        response = session.get("https://api.gizmott.com/api/v1/schedule/fastchannelsv2?timezone=Asia%2FJakarta", headers=headers, timeout=15)
        if response.status_code != 200: return

        valid_programmes = []
        for channel_item in response.json().get("data", {}).get("schedules", []):
            if not isinstance(channel_item, dict): continue
            channel_id = str(channel_item.get("channel_id") or channel_item.get("id") or "channel")
            if channel_id not in channels_map:
                channels_map[channel_id] = channel_item.get("channel_name") or f"Channel {channel_id}"

            for item in channel_item.get("schedules", []) or channel_item.get("programs", []) or [channel_item]:
                if not isinstance(item, dict): continue
                title = item.get("title", "Live Event")
                desc = item.get("description", "")
                if not desc or desc.strip().lower() in ["none", "null"]: desc = ""
                
                start_fmt = parse_time_to_xmltv(item.get("start", ""))
                stop_fmt = parse_time_to_xmltv(item.get("end", "") or item.get("stop", ""))

                if start_fmt and stop_fmt:
                    valid_programmes.append({
                        "channel": channel_id, "start": start_fmt, "stop": stop_fmt,
                        "title": html.escape(str(title)), "desc": html.escape(str(desc)),
                    })

        with open("epg.xml", "w", encoding="utf-8") as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n<tv>\n')
            for ch_id, ch_name in channels_map.items():
                f.write(f'  <channel id="{ch_id}">\n    <display-name lang="en">{html.escape(ch_name)}</display-name>\n  </channel>\n')
            for prog in valid_programmes:
                f.write(f'  <programme start="{prog["start"]}" stop="{prog["stop"]}" channel="{prog["channel"]}">\n')
                f.write(f'    <title lang="en">{prog["title"]}</title>\n')
                if prog["desc"]: f.write(f'    <desc lang="en">{prog["desc"]}</desc>\n')
                f.write('  </programme>\n')
            f.write("</tv>\n")
        print(f"FLS EPG Success! Total programs: {len(valid_programmes)}")
    except Exception as e:
        print(f"Error processing FLS EPG: {e}")

if __name__ == "__main__":
    generate_epg()
