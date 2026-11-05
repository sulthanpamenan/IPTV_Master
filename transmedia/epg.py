from datetime import datetime, timedelta
import cloudscraper
import json
import html
import re
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
import requests
import logging
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import create_robust_session, clean_xml_text

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)

def get_transtv_schedule(date_str=None, session=None):
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")

    url = "https://www.transtv.co.id/schedule"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Referer": "https://www.transtv.co.id/",
    }

    programs = []
    active_session = session if session else create_robust_session()
    
    try:
        response = active_session.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            logging.warning(f"Failed to access the Trans TV website ({date_str}), status code: {response.status_code}")
            return programs

        soup = BeautifulSoup(response.text, "html.parser")
        date_section = soup.find("section", id=date_str)
        if not date_section:
            logging.warning(f"The Trans TV schedule for {date_str} was not found on the page.")
            return programs

        prog_elements = date_section.find_all("div", class_="sche__programsList")

        for prog in prog_elements:
            time_elem = prog.find("h6")
            title_elem = prog.find("a")

            time_text = time_elem.get_text(strip=True) if time_elem else ""
            raw_title = title_elem.get_text(strip=True) if title_elem else ""
            link = title_elem.get("href") if title_elem else ""

            if not re.match(r"^\d{2}:\d{2}$", time_text):
                continue

            clean_title = clean_xml_text(html.unescape(raw_title)).upper()
            if time_text and clean_title:
                programs.append({
                    "date": date_str,
                    "start": time_text,
                    "end": "",  
                    "title": clean_title,
                    "link": link,
                    "desc": "",
                    "category": "General",
                })
    except Exception as e:
        logging.error(f"Error while parsing Trans TV for {date_str}: {e}")

    return programs

def get_transtv_multi_day_schedule(days_ahead=2):
    all_programs = []
    session = create_robust_session()
    today = datetime.now()
    target_dates = [(today + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days_ahead)]
    
    def fetch_day(date_str):
        return get_transtv_schedule(date_str, session=session)

    with ThreadPoolExecutor(max_workers=5) as executor:
        results = executor.map(fetch_day, target_dates)
        for daily_progs in results:
            all_programs.extend(daily_progs)
            
    return all_programs

def get_trans7_multi_day_schedule(days_ahead=2):
    all_programs = []
    scraper = cloudscraper.create_scraper()
    base_url = "https://sevenhub.id/live"
    build_id = None

    try:
        logging.info("Fetching Trans 7 main page to extract buildId...")
        res_main = scraper.get(base_url, timeout=15)
        
        if res_main.status_code == 200:
            soup = BeautifulSoup(res_main.text, "html.parser")
            script_tag = soup.find("script", id="__NEXT_DATA__")
            
            if script_tag and script_tag.string:
                try:
                    next_data = json.loads(script_tag.string)
                    build_id = next_data.get("buildId")
                except Exception:
                    pass
            
            if not build_id:
                match = re.search(r'"buildId"\s*:\s*"([^"]+)"', res_main.text)
                if match:
                    build_id = match.group(1)

        if not build_id:
            build_id = "CIO-V18echGfrT93WPcqd"

        url = f"https://sevenhub.id/_next/data/{build_id}/live.json"
        res = scraper.get(url, timeout=15)
        
        if res.status_code == 200:
            data = res.json()
            schedules_data = data.get("pageProps", {}).get("schedules", {})
            week_schedules = schedules_data.get("weekSchedules", {}).get("data", [])
            
            if not week_schedules:
                main_sched = schedules_data.get("data", {})
                if main_sched:
                    week_schedules = [main_sched]

            today = datetime.now()
            target_dates = [(today + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days_ahead)]

            for day_sched in week_schedules:
                if not isinstance(day_sched, dict):
                    continue
                date_str = day_sched.get("date_schedule_tv") or day_sched.get("date_schedule")
                if date_str in target_dates:
                    schedule_list = day_sched.get("data_schedule_tv") or day_sched.get("data_schedule", [])
                    if not isinstance(schedule_list, list):
                        continue

                    for item in schedule_list:
                        if not isinstance(item, dict):
                            continue
                        raw_title = item.get("program", "")
                        start_time = item.get("time_start", "")
                        end_time = item.get("time_end", "")
                        
                        if not start_time:
                            continue

                        clean_title = clean_xml_text(html.unescape(raw_title)).upper()
                        if start_time and clean_title:
                            all_programs.append({
                                "date": date_str,
                                "start": start_time,
                                "end": end_time,
                                "title": clean_title,
                                "desc": "",
                                "category": "General",
                            })
    except Exception as e:
        logging.error(f"Error in Trans 7 Multi-Day EPG: {e}")

    return all_programs

def format_xmltv_date(dt):
    return dt.strftime("%Y%m%d%H%M%S +0700")

def build_xmltv(transtv_progs, trans7_progs):
    tv = ET.Element("tv", {"generator-info-name": "Transmedia EPG Generator"})
    channels_data = [
        {"id": "transtv", "name": "Trans TV"},
        {"id": "trans7", "name": "Trans 7"},
    ]

    for ch in channels_data:
        channel_elem = ET.SubElement(tv, "channel", {"id": ch["id"]})
        ET.SubElement(channel_elem, "display-name").text = ch["name"]

    for ch_id, progs in [("transtv", transtv_progs), ("trans7", trans7_progs)]:
        for i, p in enumerate(progs):
            prog_date_str = p.get("date", datetime.now().strftime("%Y-%m-%d"))
            try:
                p_date = datetime.strptime(prog_date_str, "%Y-%m-%d").date()
                sh, sm = map(int, p["start"].split(":"))
                start_dt = datetime(p_date.year, p_date.month, p_date.day, sh, sm)

                if p.get("end") and re.match(r"^\d{2}:\d{2}$", p["end"]):
                    eh, em = map(int, p["end"].split(":"))
                    end_dt = datetime(p_date.year, p_date.month, p_date.day, eh, em)
                    if end_dt <= start_dt:
                        end_dt += timedelta(days=1)
                else:
                    if i < len(progs) - 1 and progs[i + 1].get("date") == prog_date_str:
                        nh, nm = map(int, progs[i + 1]["start"].split(":"))
                        end_dt = datetime(p_date.year, p_date.month, p_date.day, nh, nm)
                        if end_dt <= start_dt:
                            end_dt += timedelta(days=1)
                    else:
                        end_dt = start_dt + timedelta(hours=1, minutes=30)

                prog_elem = ET.SubElement(tv, "programme", {
                    "start": format_xmltv_date(start_dt),
                    "stop": format_xmltv_date(end_dt),
                    "channel": ch_id,
                })
                ET.SubElement(prog_elem, "title", {"lang": "id"}).text = p["title"]
                ET.SubElement(prog_elem, "desc", {"lang": "id"}).text = p.get("desc", "")
                ET.SubElement(prog_elem, "category", {"lang": "id"}).text = p.get("category", "General")
            except Exception:
                continue

    tree = ET.ElementTree(tv)
    try:
        ET.indent(tree, space="  ")
    except AttributeError:
        pass
    tree.write("epg.xml", encoding="utf-8", xml_declaration=True)
    logging.info("transmedia/epg.xml successfully created!")

if __name__ == "__main__":
    t_tv = get_transtv_multi_day_schedule(days_ahead=2)
    t_7 = get_trans7_multi_day_schedule(days_ahead=2)
    build_xmltv(t_tv, t_7)
