import base64
import html
import io
import json
import os
import re
import threading
import time
import urllib3
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import pandas as pd
import requests
from bs4 import BeautifulSoup

from utils import (
    clean_url_str,
    clean_xml_text,
    create_robust_session,
    extract_icon_from_any,
    load_json_cache,
    save_json_cache,
)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
}

HTTP_SESSION = create_robust_session(HEADERS)

TIME_PATTERN_HM = re.compile(r"(\b[0-2]?\d[:.][0-5]\d\b)")
TIME_PATTERN_AMPM = re.compile(r"(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm))", re.IGNORECASE)

EPG_TARGET_SOURCES = [
    # 1. TP CHANNEL THAILAND
    {"id": "TPChannel.th", "name": "TP Channel", "url": "https://www.tpchannel.org/tv/schedule", "utc_offset": "+0700"},

    # 2. RED BULL TV CHANNELS
    {"id": "RedBullTV.global", "name": "Red Bull TV: World of Red Bull", "rrn": "rrn:content:video-channels:c81f8686-ab67-4965-ba04-5f6658bb96cc", "utc_offset": "+0700"},
    {"id": "RedBullPadel.global", "name": "Red Bull TV: Padel", "rrn": "rrn:content:video-channels:e0e6dee0-8c39-4de1-9488-72828468efe0", "utc_offset": "+0700"},
    {"id": "RedBullBike.global", "name": "Red Bull TV: Bike", "rrn": "rrn:content:video-channels:ee30c528-32b1-4604-8976-e3bcee4ae7f0", "utc_offset": "+0700"},
    {"id": "RedBullAdventure.global", "name": "Red Bull TV: Adventure", "rrn": "rrn:content:video-channels:870bcfa8-62b1-4e84-9c85-39f083df368a", "utc_offset": "+0700"},
    {"id": "RedBullMotorsports.global", "name": "Red Bull TV: Motorsports", "rrn": "rrn:content:video-channels:fd4ed3c9-1800-477b-9909-53255da06632", "utc_offset": "+0700"},
    {"id": "RedBullSurfing.global", "name": "Red Bull TV: Surfing", "rrn": "rrn:content:video-channels:2f6afaec-7ade-4fb8-961a-a51aa8279a99", "utc_offset": "+0700"},
    {"id": "RedBullSkateboarding.global", "name": "Red Bull TV: Skateboarding", "rrn": "rrn:content:video-channels:5021f46c-6f34-4f51-ba1f-967f2885ac97", "utc_offset": "+0700"},
    {"id": "RedBullWinter.global", "name": "Red Bull TV: Winter", "rrn": "rrn:content:video-channels:f4aa4fe4-5ce6-4b1c-a60b-abc6f21f16d0", "utc_offset": "+0700"},
    {"id": "RedBullActionReel.global", "name": "Red Bull TV: Action Reel", "rrn": "rrn:content:video-channels:69a66f02-21fd-42a1-be5b-6965541cfe6a", "utc_offset": "+0700"},

    # 3. CLTV36 PHILIPPINES
    {"id": "CLTV36.ph", "name": "CLTV36", "url": "https://cltv36.tv/tv-programs/", "utc_offset": "+0800"},

    # 4. QAZAQSTAN NETWORK
    {"id": "Qazaqstan.kz", "name": "Qazaqstan TV", "url": "https://qazaqstan.tv/program", "utc_offset": "+0500"},
    {"id": "QazaqstanInt.kz", "name": "Qazaqstan International", "url": "https://qazaqstan.tv/program", "utc_offset": "+0500"},
    {"id": "Balapan.kz", "name": "Balapan TV", "url": "https://balapan.tv/program", "utc_offset": "+0500"},
    {"id": "AbaiTV.kz", "name": "Abai TV", "url": "https://abaitv.kz/kz/program", "utc_offset": "+0500"},
    {"id": "Qazsport.kz", "name": "Qazsport", "url": "https://qazsporttv.kz/kz/program", "utc_offset": "+0500"},
    {"id": "AqjaiyqTV.kz", "name": "Aqjaiyq TV", "url": "https://aqjaiyqtv.kz/kz/program", "utc_offset": "+0500"},
    {"id": "AqtobeTV.kz", "name": "Aqtobe TV", "url": "https://aqtobetv.kz/kz/program", "utc_offset": "+0500"},
    {"id": "AltaiTV.kz", "name": "Altai TV", "url": "https://altaitv.kz/kz/program", "utc_offset": "+0500"},
    {"id": "AtyrauTV.kz", "name": "Atyrau TV", "url": "https://atyrautv.kz/kz/program", "utc_offset": "+0500"},
    {"id": "ErtisTV.kz", "name": "Ertis TV", "url": "https://ertistv.kz/kz/program", "utc_offset": "+0500"},
    {"id": "JambylTV.kz", "name": "Jambyl TV", "url": "https://jambyltv.kz/kz/program", "utc_offset": "+0500"},
    {"id": "KoksheTV.kz", "name": "Kokshe TV", "url": "https://kokshetv.kz/kz/program", "utc_offset": "+0500"},
    {"id": "MangystauTV.kz", "name": "Mangystau TV", "url": "https://mangystautv.kz/kz/program", "utc_offset": "+0500"},
    {"id": "OntustikTV.kz", "name": "Ontustik TV", "url": "https://ontustiktv.kz/kz/program", "utc_offset": "+0500"},
    {"id": "QostanaiTV.kz", "name": "Qostanai TV", "url": "https://qostanaitv.kz/kz/program", "utc_offset": "+0500"},
    {"id": "QyzyljarTV.kz", "name": "Qyzyljar TV", "url": "https://qyzyljartv.kz/kz/program", "utc_offset": "+0500"},
    {"id": "QyzylordaTV.kz", "name": "Qyzylorda TV", "url": "https://qyzylordatv.kz/kz/program", "utc_offset": "+0500"},
    {"id": "SaryarqaTV.kz", "name": "Saryarqa TV", "url": "https://saryarqatv.kz/kz/program", "utc_offset": "+0500"},
    {"id": "SemeiTV.kz", "name": "Semei TV", "url": "https://semeitv.kz/kz/program", "utc_offset": "+0500"},

    # 5. INDONESIANA TV
    {"id": "Indonesiana_MMF.id", "name": "Indonesiana TV MMF", "code": "MMF", "utc_offset": "+0700"},
    {"id": "Indonesiana_MKU.id", "name": "Indonesiana TV MKU", "code": "MKU", "utc_offset": "+0700"},

    # 6. KBS WORLD
    {"id": "KBSWorld.id", "name": "KBS World", "utc_offset": "+0700"},
]


def format_xmltv_date(dt_obj, utc_offset="+0700"):
    return dt_obj.strftime(f"%Y%m%d%H%M%S {utc_offset}")


def get_now_in_channel_tz(offset_str):
    sign = -1 if offset_str[0] == "-" else 1
    hours = int(offset_str[1:3])
    return datetime.now(timezone.utc) + timedelta(hours=sign * hours)


def clean_text_str(val):
    if not val:
        return ""
    text = str(val).replace("\xa0", " ")
    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", " ", text).strip()
    return re.sub(r"\s+", " ", text)


def decode_base64_json(data_b64):
    if not data_b64:
        return None
    try:
        raw = str(data_b64).strip()
        padding = "=" * (-len(raw) % 4)
        decoded_bytes = base64.b64decode(raw + padding)
        return json.loads(decoded_bytes.decode("utf-8"))
    except Exception:
        return None


def _extract_balanced_json_assignment(text, var_pattern, open_char, close_char):
    """Mengekstrak nilai JSON seimbang (bracket/brace matching) setelah assignment variabel JS."""
    results = []
    decoder = json.JSONDecoder()
    for match in re.finditer(var_pattern, text):
        var_name = match.group(1) if match.lastindex else ""
        idx = match.end()
        while idx < len(text) and text[idx].isspace():
            idx += 1
        if idx >= len(text) or text[idx] != open_char:
            continue
        try:
            obj, _ = decoder.raw_decode(text[idx:])
            if open_char == "[" and isinstance(obj, list):
                results.append((var_name, obj))
            elif open_char == "{" and isinstance(obj, dict):
                results.append((var_name, obj))
        except json.JSONDecodeError:
            continue
    return results


# --- 1. TIVIE.ID MODULE ---
CF_WORKER_URL = "https://tivie-proxy.sulthan-pamenan.workers.dev"
TIVIE_CACHE_DIR = "Cache"
TIVIE_PROGRAM_CACHE_FILE = os.path.join(TIVIE_CACHE_DIR, "tivie_program_cache.json")
TIVIE_CHANNELS_CACHE_FILE = os.path.join(TIVIE_CACHE_DIR, "tivie_channels_cache.json")
TIVIE_DETAIL_TTL_SECONDS = 7 * 24 * 3600

TIVIE_PROGRAM_DETAIL_CACHE = {}
TIVIE_CHANNEL_ICON_CACHE = {}
TIVIE_CACHE_LOCK = threading.Lock()
TIVIE_DISK_LOADED = False

TIVIE_MASTER_FALLBACK = [
    {"id": "antv", "name": "ANTV"}, {"id": "btv", "name": "BTV"},
    {"id": "cnnindonesia", "name": "CNN Indonesia"}, {"id": "garudatv", "name": "Garuda TV"},
    {"id": "gtv", "name": "GTV"}, {"id": "indosiar", "name": "Indosiar"},
    {"id": "inews", "name": "iNews"}, {"id": "kompastv", "name": "Kompas TV"},
    {"id": "mdtv", "name": "MDTV"}, {"id": "mentaritv", "name": "Mentari TV"},
    {"id": "metrotv", "name": "Metro TV"}, {"id": "mnctv", "name": "MNC TV"},
    {"id": "moji", "name": "MOJI"}, {"id": "nusantaratv", "name": "Nusantara TV"},
    {"id": "rcti", "name": "RCTI"}, {"id": "rtv", "name": "RTV"},
    {"id": "sctv", "name": "SCTV"}, {"id": "sinpotv", "name": "Sin Po TV"},
    {"id": "transtv", "name": "Trans TV"}, {"id": "trans7", "name": "Trans 7"},
    {"id": "tvone", "name": "tvOne"}, {"id": "tvri", "name": "TVRI"},
    {"id": "vtv", "name": "VTV"}, {"id": "sindonews", "name": "Sindonews TV"},
    {"id": "axn", "name": "AXN"}, {"id": "beinsports1", "name": "beIN Sports 1"},
    {"id": "beinsports2", "name": "beIN Sports 2"}, {"id": "beinsports3", "name": "beIN Sports 3"},
    {"id": "ccm", "name": "CCM"}, {"id": "celestialmovies", "name": "Celestial Movies"},
    {"id": "cinemaworld", "name": "CinemaWorld"}, {"id": "cinemax", "name": "Cinemax"},
    {"id": "galaxy", "name": "Galaxy"}, {"id": "galaxypremium", "name": "Galaxy Premium"},
    {"id": "hbo", "name": "HBO"}, {"id": "hbofamily", "name": "HBO Family"},
    {"id": "hbohits", "name": "HBO Hits"}, {"id": "hbosignature", "name": "HBO Signature"},
    {"id": "hits", "name": "HITS"}, {"id": "hitsmovies", "name": "HITS Movies"},
    {"id": "hitsnow", "name": "HITS Now"}, {"id": "imc", "name": "IMC"},
    {"id": "kplus", "name": "K-Plus"}, {"id": "kix", "name": "KIX"},
    {"id": "lifetime", "name": "Lifetime"}, {"id": "rockaction", "name": "Rock Action"},
    {"id": "rockentertainment", "name": "Rock Entertainment"}, {"id": "spotv", "name": "SpoTV"},
    {"id": "spotv2", "name": "SpoTV2"}, {"id": "studiouniversal", "name": "Studio Universal"},
    {"id": "thrill", "name": "Thrill"}, {"id": "tvn", "name": "tvN"},
    {"id": "tvnmovies", "name": "tvN Movies"}, {"id": "warner", "name": "Warner TV"},
    {"id": "zeebioskop", "name": "Zee Bioskop"},
]


def _ensure_tivie_disk_cache_loaded():
    global TIVIE_DISK_LOADED
    with TIVIE_CACHE_LOCK:
        if TIVIE_DISK_LOADED:
            return
        disk_progs = load_json_cache(TIVIE_PROGRAM_CACHE_FILE, max_age_seconds=TIVIE_DETAIL_TTL_SECONDS)
        if isinstance(disk_progs, dict):
            for k, v in disk_progs.items():
                if isinstance(v, dict) and k not in TIVIE_PROGRAM_DETAIL_CACHE:
                    TIVIE_PROGRAM_DETAIL_CACHE[k] = {
                        "icon": clean_url_str(v.get("icon", "")),
                        "category": clean_xml_text(v.get("category", "")),
                        "subtitle": clean_xml_text(v.get("subtitle", "")),
                        "desc": clean_xml_text(v.get("desc", "")),
                    }

        disk_chs = load_json_cache(TIVIE_CHANNELS_CACHE_FILE, max_age_seconds=TIVIE_DETAIL_TTL_SECONDS)
        if isinstance(disk_chs, dict):
            for real_id, info in disk_chs.items():
                if isinstance(info, dict):
                    icon_url = clean_url_str(info.get("icon", ""))
                    if icon_url and real_id not in TIVIE_CHANNEL_ICON_CACHE:
                        TIVIE_CHANNEL_ICON_CACHE[real_id] = icon_url

        TIVIE_DISK_LOADED = True


def _persist_tivie_caches():
    with TIVIE_CACHE_LOCK:
        prog_snapshot = dict(TIVIE_PROGRAM_DETAIL_CACHE)
        ch_snapshot = {k: {"icon": v} for k, v in TIVIE_CHANNEL_ICON_CACHE.items() if v}
    if prog_snapshot:
        save_json_cache(TIVIE_PROGRAM_CACHE_FILE, prog_snapshot)
    if ch_snapshot:
        save_json_cache(TIVIE_CHANNELS_CACHE_FILE, ch_snapshot)


def discover_tivie_channels():
    _ensure_tivie_disk_cache_loaded()
    channels, added_ids = [], set()
    for m_ch in TIVIE_MASTER_FALLBACK:
        real_id = m_ch["id"]
        if real_id not in added_ids:
            added_ids.add(real_id)
            channels.append({
                "id": f"Tivie_{real_id}.id",
                "real_id": real_id,
                "name": m_ch["name"],
                "icon": TIVIE_CHANNEL_ICON_CACHE.get(real_id, ""),
            })
    return channels


def _normalize_tivie_program_url(href_val):
    if not href_val:
        return ""
    raw = str(href_val).strip()
    if raw.startswith(("http://", "https://")):
        return raw if "/program/" in raw else ""
    if raw.startswith("/program/"):
        return f"https://tivie.id{raw}"
    return ""


def _build_tivie_proxy_program_url(program_url):
    match = re.search(r"https?://[^/]+(/program/[^?#]+)", program_url)
    if match and CF_WORKER_URL:
        return f"{CF_WORKER_URL.rstrip('/')}{match.group(1)}"
    return program_url


def fetch_tivie_program_detail(program_url):
    _ensure_tivie_disk_cache_loaded()
    clean_prog_url = _normalize_tivie_program_url(program_url)
    if not clean_prog_url:
        return {"icon": "", "category": "", "subtitle": "", "desc": ""}

    cache_key = clean_prog_url.split("?")[0]
    with TIVIE_CACHE_LOCK:
        if cache_key in TIVIE_PROGRAM_DETAIL_CACHE:
            return TIVIE_PROGRAM_DETAIL_CACHE[cache_key]

    detail = {"icon": "", "category": "", "subtitle": "", "desc": ""}
    candidate_urls = []
    proxy_url = _build_tivie_proxy_program_url(clean_prog_url)
    if proxy_url:
        candidate_urls.append(proxy_url)
    if clean_prog_url not in candidate_urls:
        candidate_urls.append(clean_prog_url)

    for target_url in candidate_urls:
        try:
            res = HTTP_SESSION.get(
                target_url,
                headers={
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "id,en-US;q=0.9,en;q=0.8",
                    "Referer": "https://tivie.id/",
                },
                timeout=12,
            )
            if res.status_code != 200 or not res.text:
                continue

            soup = BeautifulSoup(res.text, "html.parser")
            main_el = soup.find("main", id="main-content") or soup.find("main") or soup

            poster_el = main_el.select_one("div.aspect-video img[src], img[src*='/tivie/poster/']")
            if poster_el:
                detail["icon"] = extract_icon_from_any(poster_el.get("src") or "")
            if not detail["icon"]:
                og_img = soup.find("meta", property="og:image")
                if og_img and og_img.get("content"):
                    detail["icon"] = extract_icon_from_any(og_img.get("content"))

            cats = []
            for cat_link in main_el.select("a[href*='/programs/']"):
                c_txt = clean_xml_text(cat_link.get_text(" ", strip=True))
                if c_txt and len(c_txt) <= 40 and c_txt.lower() not in {"semua", "all", "program", "programs"}:
                    if c_txt not in cats:
                        cats.append(c_txt)
            if cats:
                detail["category"] = " / ".join(cats[:2])

            h1_el = main_el.find("h1")
            if h1_el:
                h1_txt = clean_xml_text(h1_el.get_text(" ", strip=True))
                ep_match = re.search(r"\b(?:eps?\.?|episode|season\s*\d+|part\s*\d+)\s*[:#-]?\s*\d+\b", h1_txt, re.I)
                if ep_match:
                    detail["subtitle"] = ep_match.group(0).strip()

            h2_el = main_el.find("h2")
            if h2_el:
                if h2_el.parent:
                    for hidden_el in h2_el.parent.select(".hide"):
                        hidden_el.decompose()
                p_el = h2_el.find_next("p")
                if p_el:
                    for hidden_el in p_el.select(".hide"):
                        hidden_el.decompose()
                    p_text = clean_xml_text(p_el.get_text(" ", strip=True))
                    if p_text and not p_text.lower().startswith("jadwal siaran tayangan"):
                        detail["desc"] = p_text

            if not detail["desc"]:
                meta_desc = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", property="og:description")
                if meta_desc and meta_desc.get("content"):
                    m_txt = clean_xml_text(meta_desc.get("content"))
                    if m_txt and not m_txt.lower().startswith("jadwal siaran tayangan"):
                        detail["desc"] = m_txt

            if detail["icon"] or detail["category"] or detail["desc"] or detail["subtitle"]:
                break
        except Exception:
            continue

    with TIVIE_CACHE_LOCK:
        TIVIE_PROGRAM_DETAIL_CACHE[cache_key] = detail

    return detail


def resolve_tivie_details_batch(prog_urls, max_workers=10):
    _ensure_tivie_disk_cache_loaded()
    pending_urls = []
    seen_keys = set()

    for u in prog_urls:
        norm = _normalize_tivie_program_url(u)
        if not norm:
            continue
        key = norm.split("?")[0]
        if key in seen_keys:
            continue
        seen_keys.add(key)
        with TIVIE_CACHE_LOCK:
            already_cached = key in TIVIE_PROGRAM_DETAIL_CACHE
        if not already_cached:
            pending_urls.append(norm)

    if not pending_urls:
        return

    with ThreadPoolExecutor(max_workers=min(max_workers, len(pending_urls))) as executor:
        list(executor.map(fetch_tivie_program_detail, pending_urls))


def scrape_single_tivie_channel(ch):
    _ensure_tivie_disk_cache_loaded()
    ch_id, real_id, ch_name = ch["id"], ch["real_id"], ch["name"]
    ch_icon = clean_url_str(ch.get("icon", "")) or TIVIE_CHANNEL_ICON_CACHE.get(real_id, "")
    url = f"{CF_WORKER_URL}/channel/{real_id}"
    draft_programmes = []
    urls_to_resolve = []
    programmes = []

    try:
        res = HTTP_SESSION.get(
            url,
            headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "id,en-US;q=0.9,en;q=0.8",
            },
            timeout=15,
        )
        if res.status_code == 200 and res.text:
            soup = BeautifulSoup(res.text, "html.parser")
            logo_img = soup.select_one(
                "img[src*='/tivie/channel/'], img[alt*='logo' i], img.channel-logo, .channel-header img"
            )
            if logo_img and logo_img.get("src"):
                parsed_logo = extract_icon_from_any(logo_img.get("src"))
                if parsed_logo:
                    ch_icon = parsed_logo
                    with TIVIE_CACHE_LOCK:
                        TIVIE_CHANNEL_ICON_CACHE[real_id] = ch_icon

            title_to_prog_url = {}
            for a_tag in soup.select("a[href*='/program/']"):
                p_url = _normalize_tivie_program_url(a_tag.get("href"))
                if not p_url:
                    continue
                a_text = clean_xml_text(a_tag.get_text(" ", strip=True)).lower()
                if a_text and a_text not in title_to_prog_url:
                    title_to_prog_url[a_text] = p_url

            json_ld_scripts = soup.find_all("script", type="application/ld+json")
            for script in json_ld_scripts:
                if not script.string:
                    continue
                try:
                    data = json.loads(script.string)
                    items = data if isinstance(data, list) else [data]

                    for item in items:
                        if not isinstance(item, dict):
                            continue
                        if item.get("@type") == "BroadcastEvent":
                            start_iso = item.get("startDate")
                            end_iso = item.get("endDate")
                            name = clean_xml_text(item.get("name", ""))
                            desc = clean_xml_text(item.get("description", ""))
                            category = clean_xml_text(item.get("genre") or "")
                            prog_icon = extract_icon_from_any(
                                item.get("image") or item.get("thumbnailUrl") or ""
                            )

                            if not start_iso or not end_iso or not name:
                                continue

                            prog_url = _normalize_tivie_program_url(item.get("url") or "")
                            if not prog_url:
                                prog_url = title_to_prog_url.get(name.lower(), "")

                            if prog_url and (not prog_icon or not category or not desc):
                                urls_to_resolve.append(prog_url)

                            start_dt = datetime.fromisoformat(start_iso)
                            stop_dt = datetime.fromisoformat(end_iso)

                            draft_programmes.append({
                                "channel": ch_id,
                                "start": format_xmltv_date(start_dt, "+0700"),
                                "stop": format_xmltv_date(stop_dt, "+0700"),
                                "title": name,
                                "subtitle": "",
                                "desc": desc,
                                "category": category,
                                "icon": prog_icon,
                                "prog_url": prog_url,
                                "lang": "id",
                            })
                except (json.JSONDecodeError, TypeError, ValueError):
                    continue

        if urls_to_resolve:
            resolve_tivie_details_batch(urls_to_resolve, max_workers=8)

        for p in draft_programmes:
            prog_url = p.pop("prog_url", "")
            if prog_url:
                extra = fetch_tivie_program_detail(prog_url)
                if not p["icon"] and extra.get("icon"):
                    p["icon"] = extra["icon"]
                if not p["category"] and extra.get("category"):
                    p["category"] = extra["category"]
                if not p["subtitle"] and extra.get("subtitle"):
                    p["subtitle"] = extra["subtitle"]
                if not p["desc"] and extra.get("desc"):
                    p["desc"] = extra["desc"]
            programmes.append(p)

        if programmes:
            print(f"[✓] Tivie.id [{ch_name}]: Successfully loaded {len(programmes)} programs!")

    except Exception as e:
        print(f"[!] Tivie Error [{ch_name}]: {e}")

    return {"id": ch_id, "name": ch_name, "icon": ch_icon}, programmes


def fetch_all_tivie_parallel():
    channels = discover_tivie_channels()
    print(f"[*] Starting parallel EPG extraction for {len(channels)} Tivie.id channels...")
    all_channels, all_programmes = [], []

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = executor.map(scrape_single_tivie_channel, channels)
        for ch_info, progs in results:
            if progs:
                all_channels.append(ch_info)
                all_programmes.extend(progs)

    _persist_tivie_caches()
    print(f"[✓] Tivie.id: Successfully extracted {len(all_channels)} active channels & {len(all_programmes)} programs!")
    return all_channels, all_programmes


# --- 2. DENS.TV MODULE ---
DENS_CACHE_DIR = "Cache"
DENS_CHANNELS_CACHE_FILE = os.path.join(DENS_CACHE_DIR, "dens_channels_cache.json")
DENS_CACHE_TTL_SECONDS = 7 * 24 * 3600

DENS_CHANNEL_ICON_CACHE = {}
DENS_CACHE_LOCK = threading.Lock()
DENS_DISK_LOADED = False

DENS_PLACEHOLDER_TITLES = {
    "the schedule is not available",
    "schedule not available",
    "no schedule available",
}

DENS_FALLBACK_CATEGORIES = ["tv-local", "tv-premium", "tv-international", "tv-free-streaming"]


def _ensure_dens_disk_cache_loaded():
    global DENS_DISK_LOADED
    with DENS_CACHE_LOCK:
        if DENS_DISK_LOADED:
            return
        disk_chs = load_json_cache(DENS_CHANNELS_CACHE_FILE, max_age_seconds=DENS_CACHE_TTL_SECONDS)
        if isinstance(disk_chs, dict):
            for ch_key, info in disk_chs.items():
                if isinstance(info, dict):
                    icon_url = clean_url_str(info.get("icon", ""))
                    if icon_url and ch_key not in DENS_CHANNEL_ICON_CACHE:
                        DENS_CHANNEL_ICON_CACHE[ch_key] = icon_url
        DENS_DISK_LOADED = True


def _persist_dens_caches():
    with DENS_CACHE_LOCK:
        ch_snapshot = {k: {"icon": v} for k, v in DENS_CHANNEL_ICON_CACHE.items() if v}
    if ch_snapshot:
        save_json_cache(DENS_CHANNELS_CACHE_FILE, ch_snapshot)


def get_official_dens_channels():
    return [
        {"id_num": "3", "slug": "live-streaming-1", "id": "Dens_live-streaming-1.id", "name": "Live Streaming 1", "cat": "tv-local"},
        {"id_num": "107", "slug": "densplay", "id": "Dens_densplay.id", "name": "DensPlay", "cat": "tv-local"},
        {"id_num": "42", "slug": "denslifestyle", "id": "Dens_denslifestyle.id", "name": "Dens Lifestyle", "cat": "tv-local"},
        {"id_num": "117", "slug": "densfood-channel", "id": "Dens_densfood-channel.id", "name": "Dens Food Channel", "cat": "tv-local"},
        {"id_num": "102", "slug": "densshowbiz", "id": "Dens_densshowbiz.id", "name": "Dens ShowBiz", "cat": "tv-local"},
        {"id_num": "1", "slug": "densknowledge", "id": "Dens_densknowledge.id", "name": "Dens Knowledge", "cat": "tv-local"},
        {"id_num": "137", "slug": "channel-jowo", "id": "Dens_channel-jowo.id", "name": "Channel Jowo", "cat": "tv-local"},
        {"id_num": "131", "slug": "berita-satu", "id": "Dens_berita-satu.id", "name": "BeritaSatu World", "cat": "tv-local"},
        {"id_num": "94", "slug": "elshinta-tv", "id": "Dens_elshinta-tv.id", "name": "Elshinta TV", "cat": "tv-local"},
        {"id_num": "122", "slug": "magna-channel", "id": "Dens_magna-channel.id", "name": "Magna Channel", "cat": "tv-local"},
        {"id_num": "118", "slug": "tvri-sport", "id": "Dens_tvri-sport.id", "name": "TVRI Sport", "cat": "tv-local"},
        {"id_num": "112", "slug": "jak-tv", "id": "Dens_jak-tv.id", "name": "Jak TV", "cat": "tv-local"},
        {"id_num": "21", "slug": "rodjatv", "id": "Dens_rodjatv.id", "name": "Rodja TV", "cat": "tv-local"},
        {"id_num": "23", "slug": "daai-tv", "id": "Dens_daai-tv.id", "name": "DAAI TV", "cat": "tv-local"},
        {"id_num": "92", "slug": "my-cinema-europe-hd", "id": "Dens_my-cinema-europe-hd.id", "name": "My Cinema Europe", "cat": "tv-premium"},
        {"id_num": "127", "slug": "crema-tv", "id": "Dens_crema-tv.id", "name": "Crema TV", "cat": "tv-premium"},
        {"id_num": "143", "slug": "qwest-tv", "id": "Dens_qwest-tv.id", "name": "Qwest TV", "cat": "tv-premium"},
        {"id_num": "128", "slug": "stingray-classica", "id": "Dens_stingray-classica.id", "name": "Stingray Classica", "cat": "tv-premium"},
        {"id_num": "130", "slug": "dance-tv", "id": "Dens_dance-tv.id", "name": "Dance TV", "cat": "tv-premium"},
        {"id_num": "98", "slug": "motorvision", "id": "Dens_motorvision.id", "name": "Motorvision+", "cat": "tv-premium"},
        {"id_num": "61", "slug": "cna", "id": "Dens_cna.id", "name": "CNA", "cat": "tv-international"},
        {"id_num": "77", "slug": "nhk-world-japan", "id": "Dens_nhk-world-japan.id", "name": "NHK World Japan", "cat": "tv-international"},
        {"id_num": "56", "slug": "al-jazeera-english", "id": "Dens_al-jazeera-english.id", "name": "Al Jazeera English", "cat": "tv-international"},
        {"id_num": "41", "slug": "trt-world", "id": "Dens_trt-world.id", "name": "TRT World", "cat": "tv-international"},
        {"id_num": "144", "slug": "russia-today-rt", "id": "Dens_russia-today-rt.id", "name": "RT News", "cat": "tv-international"},
        {"id_num": "79", "slug": "wion", "id": "Dens_wion.id", "name": "WION", "cat": "tv-international"},
        {"id_num": "104", "slug": "freedom", "id": "Dens_freedom.id", "name": "FreeDOM", "cat": "tv-international"},
        {"id_num": "27", "slug": "al-jazeera-arabic", "id": "Dens_al-jazeera-arabic.id", "name": "Al Jazeera Arabic", "cat": "tv-international"},
        {"id_num": "85", "slug": "cctv-4", "id": "Dens_cctv-4.id", "name": "CCTV-4", "cat": "tv-international"},
        {"id_num": "69", "slug": "france-24", "id": "Dens_france-24.id", "name": "France 24", "cat": "tv-international"},
        {"id_num": "146", "slug": "france-24-english", "id": "Dens_france-24-english.id", "name": "France 24 English", "cat": "tv-international"},
        {"id_num": "90", "slug": "tv5monde-asie", "id": "Dens_tv5monde-asie.id", "name": "TV5Monde Asie", "cat": "tv-international"},
        {"id_num": "81", "slug": "dw-tv", "id": "Dens_dw-tv.id", "name": "DW TV", "cat": "tv-international"},
        {"id_num": "132", "slug": "dim-tv", "id": "Dens_dim-tv.id", "name": "DIM TV", "cat": "tv-international"},
        {"id_num": "16", "slug": "cgtn-documentary", "id": "Dens_cgtn-documentary.id", "name": "CGTN Documentary", "cat": "tv-international"},
        {"id_num": "78", "slug": "tbn", "id": "Dens_tbn.id", "name": "TBN", "cat": "tv-international"},
        {"id_num": "88", "slug": "sunna-tv", "id": "Dens_sunna-tv.id", "name": "Saudi Sunnah TV", "cat": "tv-international"},
        {"id_num": "139", "slug": "wedotvmovies", "id": "Dens_wedotvmovies.id", "name": "wedo Movies", "cat": "tv-free-streaming"},
        {"id_num": "142", "slug": "wedotvamor", "id": "Dens_wedotvamor.id", "name": "wedo Amor", "cat": "tv-free-streaming"},
        {"id_num": "140", "slug": "wedotvbig-stories", "id": "Dens_wedotvbig-stories.id", "name": "wedo Big Stories", "cat": "tv-free-streaming"},
        {"id_num": "141", "slug": "wedosports", "id": "Dens_wedosports.id", "name": "wedoSports", "cat": "tv-free-streaming"},
    ]


def _parse_dens_dt(dt_val, tz):
    if not dt_val:
        return None
    raw = str(dt_val).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(raw[:19], fmt).replace(tzinfo=tz)
        except ValueError:
            continue
    return None


def _extract_dens_epg_items(soup, id_num):
    epg_list = []
    for script in soup.find_all("script"):
        script_txt = script.string or script.text or ""
        if "tvEpg" not in script_txt:
            continue
        for _, parsed_data in _extract_balanced_json_assignment(
            script_txt, r"\b(tvEpg\w*)\s*=\s*", "[", "]"
        ):
            epg_list.extend(parsed_data)

    if not epg_list:
        for el in soup.select(".item-schedule[data-x-content]"):
            decoded = decode_base64_json(el.get("data-x-content", ""))
            if isinstance(decoded, dict):
                epg_list.append(decoded)
            elif isinstance(decoded, list):
                epg_list.extend(x for x in decoded if isinstance(x, dict))

    ch_icon = ""
    ch_var = f"tvChannel_{id_num}"
    for script in soup.find_all("script"):
        script_txt = script.string or script.text or ""
        if ch_var not in script_txt:
            continue
        for _, ch_obj in _extract_balanced_json_assignment(
            script_txt, rf"\b({re.escape(ch_var)})\s*=\s*", "{", "}"
        ):
            default_img = (
                ch_obj.get("meta", {})
                .get("images", {})
                .get("default", "")
            )
            ch_icon = extract_icon_from_any(default_img)
            if ch_icon:
                break
        if ch_icon:
            break

    if not ch_icon:
        og_img = soup.find("meta", property="og:image")
        if og_img and og_img.get("content"):
            ch_icon = extract_icon_from_any(og_img.get("content"))

    return epg_list, ch_icon


def fetch_single_dens_channel(channel_info):
    _ensure_dens_disk_cache_loaded()
    wib_tz = timezone(timedelta(hours=7))
    ch_key = f"{channel_info['id_num']}_{channel_info['slug']}"
    ch_icon = clean_url_str(channel_info.get("icon", "")) or DENS_CHANNEL_ICON_CACHE.get(ch_key, "")

    primary_cat = channel_info.get("cat", "tv-local")
    candidate_cats = [primary_cat] + [c for c in DENS_FALLBACK_CATEGORIES if c != primary_cat]
    programmes = []

    try:
        soup = None
        active_cat = primary_cat
        for cat in candidate_cats:
            url = f"https://www.dens.tv/{cat}/watch/{channel_info['id_num']}/{channel_info['slug']}"
            res = HTTP_SESSION.get(
                url,
                headers={
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "id,en-US;q=0.9,en;q=0.8",
                    "Referer": f"https://www.dens.tv/{cat}",
                },
                timeout=15,
            )
            if res.status_code == 200 and res.text and ("tvEpg" in res.text or "item-schedule" in res.text):
                soup = BeautifulSoup(res.text, "html.parser")
                active_cat = cat
                break

        if soup is not None:
            epg_list, extracted_icon = _extract_dens_epg_items(soup, channel_info["id_num"])

            if extracted_icon:
                ch_icon = extracted_icon
                with DENS_CACHE_LOCK:
                    DENS_CHANNEL_ICON_CACHE[ch_key] = ch_icon

            raw_progs = []
            for item in epg_list:
                if not isinstance(item, dict):
                    continue
                title = clean_xml_text(clean_text_str(item.get("title", "")))
                if not title or title.lower() in DENS_PLACEHOLDER_TITLES:
                    continue

                desc = clean_xml_text(clean_text_str(item.get("description") or ""))
                start_dt = _parse_dens_dt(item.get("start_time"), wib_tz)
                end_dt = _parse_dens_dt(item.get("end_time"), wib_tz)

                if start_dt:
                    if end_dt and end_dt <= start_dt:
                        end_dt += timedelta(days=1)
                    raw_progs.append({
                        "start_dt": start_dt,
                        "end_dt": end_dt,
                        "title": title,
                        "desc": desc,
                    })

            if raw_progs:
                raw_progs.sort(key=lambda x: x["start_dt"])
                seen_keys = set()

                for i, curr in enumerate(raw_progs):
                    start_dt = curr["start_dt"]
                    stop_dt = curr["end_dt"]

                    if not stop_dt:
                        if i + 1 < len(raw_progs):
                            stop_dt = raw_progs[i + 1]["start_dt"]
                            if stop_dt <= start_dt:
                                stop_dt += timedelta(days=1)
                        else:
                            stop_dt = start_dt + timedelta(hours=1)

                    start_fmt = format_xmltv_date(start_dt, "+0700")
                    stop_fmt = format_xmltv_date(stop_dt, "+0700")
                    dedup_key = (start_fmt, curr["title"].lower())

                    if dedup_key in seen_keys:
                        continue
                    seen_keys.add(dedup_key)

                    programmes.append({
                        "channel": channel_info["id"],
                        "start": start_fmt,
                        "stop": stop_fmt,
                        "title": curr["title"],
                        "desc": curr["desc"],
                        "lang": "id",
                    })

                if programmes:
                    cat_note = f" [{active_cat}]" if active_cat != primary_cat else ""
                    print(f"[✓] Dens.TV [{channel_info['name']}]{cat_note}: Successfully loaded {len(programmes)} programs!")

    except Exception as e:
        print(f"[!] Dens.TV Error [{channel_info['name']}]: {e}")

    out_ch = {
        "id": channel_info["id"],
        "name": channel_info["name"],
        "icon": ch_icon,
    }
    return out_ch, programmes


def fetch_all_dens_parallel():
    _ensure_dens_disk_cache_loaded()
    channels_list = get_official_dens_channels()
    print(f"[*] Starting parallel EPG extraction for {len(channels_list)} Dens.TV channels...")
    all_channels, all_programmes = [], []

    with ThreadPoolExecutor(max_workers=9) as executor:
        results = executor.map(fetch_single_dens_channel, channels_list)
        for ch_info, progs in results:
            if progs:
                all_channels.append(ch_info)
                all_programmes.extend(progs)

    _persist_dens_caches()
    print(f"[✓] Dens.TV: Successfully extracted {len(all_channels)} active channels & {len(all_programmes)} programs!")
    return all_channels, all_programmes


# --- 3. INDONESIANA TV MODULE ---
def get_or_refresh_indonesiana_token(channel_code):
    auth_token = None
    cache_dir = "Cache"
    os.makedirs(cache_dir, exist_ok=True)
    cache_file = os.path.join(cache_dir, "indonesiana_cache.json")

    github_token = os.environ.get("GITHUB_TOKEN")
    gist_id = os.environ.get("GIST_ID")
    gist_filename = "indonesiana_token.json"

    if github_token and gist_id:
        try:
            gist_url = f"https://api.github.com/gists/{gist_id}"
            gist_headers = {"Authorization": f"Bearer {github_token}", "Accept": "application/vnd.github+json"}
            gist_res = requests.get(gist_url, headers=gist_headers, timeout=10)
            if gist_res.status_code == 200:
                files = gist_res.json().get("files", {})
                if gist_filename in files:
                    content = json.loads(files[gist_filename]["content"])
                    saved_token = content.get("token")
                    if saved_token:
                        try:
                            test_headers = {"authorization": f"Bearer {saved_token}", "accept": "application/json"}
                            test_res = requests.get(
                                f"https://api.indonesianatv.app/v1/users/live-streams/{channel_code}/programs?limit=1",
                                headers=test_headers,
                                timeout=8,
                            )
                            if test_res.status_code == 200 and test_res.json().get("success"):
                                return saved_token
                        except Exception:
                            pass
        except Exception:
            pass

    if not auth_token and os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cache_data = json.load(f)
                auth_token = cache_data.get("token")
        except Exception:
            pass

    if not auth_token:
        for attempt in range(3):
            try:
                session = requests.Session()
                session.headers.update({
                    "accept": "application/json, text/plain, */*",
                    "accept-language": "id,en-US;q=0.9,en-US;q=0.8",
                    "origin": "https://indonesiana.tv",
                    "referer": "https://indonesiana.tv/",
                    "user-agent": HEADERS["User-Agent"],
                })

                anon_url = "https://api.indonesianatv.app/v1/users/anon/sessions"
                anon_headers = {
                    "authorization": "Basic RjI5Q1c2NzY6dEZGNzJmNVNLN2lYbFFPTWNVYmFEVHpS",
                    "content-type": "application/json",
                }
                anon_res = session.post(anon_url, headers=anon_headers, json={}, timeout=25)

                if anon_res.status_code == 200:
                    anon_token = anon_res.json().get("data", {}).get("session", {}).get("token")
                    if anon_token:
                        email_url = "https://api.indonesianatv.app/v1/users/sessions/email"
                        email_headers = {
                            "authorization": f"Bearer {anon_token}",
                            "content-type": "application/json",
                        }
                        email_payload = {
                            "notification": {"channel": 0, "token": ""},
                            "email": os.environ.get("EMAIL"),
                            "password": os.environ.get("PASSWORD"),
                        }
                        email_res = session.post(email_url, headers=email_headers, json=email_payload, timeout=25)
                        if email_res.status_code == 200 and email_res.json().get("success"):
                            auth_token = email_res.json().get("data", {}).get("accessSession", {}).get("token")
                            break
            except Exception as e:
                print(f"[!] API Auth Exception (Attempt {attempt + 1}/3): {e}")

            time.sleep(2)

        if auth_token:
            token_payload = {"token": auth_token, "timestamp": datetime.now(timezone.utc).isoformat()}
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(token_payload, f)
            if github_token and gist_id:
                try:
                    requests.patch(
                        f"https://api.github.com/gists/{gist_id}",
                        headers={"Authorization": f"Bearer {github_token}"},
                        json={"files": {gist_filename: {"content": json.dumps(token_payload, indent=2)}}},
                        timeout=10,
                    )
                except Exception:
                    pass

    return auth_token


def fetch_epg_indonesiana_with_token(target, auth_token):
    epg_id = target["id"]
    channel_code = target.get("code")
    channels = [{"id": epg_id, "name": target["name"]}]
    programmes = []

    wib_tz = timezone(timedelta(hours=7))
    now_wib = datetime.now(timezone.utc).astimezone(wib_tz)

    start_timestamp = int(now_wib.replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
    end_timestamp = int((now_wib + timedelta(days=2)).replace(hour=23, minute=59, second=59, microsecond=0).timestamp())

    api_url = f"https://api.indonesianatv.app/v1/users/live-streams/{channel_code}/programs"
    params = {"filters[startDate]": start_timestamp, "filters[endDate]": end_timestamp, "skip": 0, "limit": 2000}
    headers = {
        "accept": "application/json, text/plain, */*",
        "authorization": f"Bearer {auth_token}",
        "origin": "https://indonesiana.tv",
        "referer": "https://indonesiana.tv/live",
        "user-agent": HEADERS["User-Agent"],
    }

    try:
        prog_res = requests.get(api_url, params=params, headers=headers, timeout=15)
        if prog_res.status_code == 200:
            prog_data = prog_res.json()
            if prog_data.get("success"):
                items = prog_data.get("data", {}).get("items", [])

                if not items:
                    print(f"[!] Indonesiana TV [{target['name']}]: No schedule items found for this date range.")
                    return channels, programmes

                for item in items:
                    title = item.get("name")
                    start_str = item.get("startDate")
                    end_str = item.get("endDate")
                    if start_str and end_str and title:
                        start_dt = datetime.fromtimestamp(int(start_str), wib_tz)
                        stop_dt = datetime.fromtimestamp(int(end_str), wib_tz)
                        programmes.append({
                            "channel": epg_id,
                            "start": format_xmltv_date(start_dt, "+0700"),
                            "stop": format_xmltv_date(stop_dt, "+0700"),
                            "title": clean_text_str(title),
                            "desc": "",
                            "lang": "id",
                        })
                print(f"[✓] Indonesiana TV [{target['name']}]: Successfully loaded {len(programmes)} programs.")
    except Exception as e:
        print(f"[!] Indonesiana TV API Error [{target['name']}]: {e}")

    return channels, programmes


def fetch_epg_indonesiana(target):
    shared_auth_token = get_or_refresh_indonesiana_token(target.get("code"))
    if shared_auth_token:
        return fetch_epg_indonesiana_with_token(target, shared_auth_token)
    print(f"[!] Indonesiana TV [{target['name']}]: Failed to obtain token.")
    return [], []


def fetch_all_indonesiana(targets):
    if not targets:
        return [], []

    shared_auth_token = None
    for target in targets:
        shared_auth_token = get_or_refresh_indonesiana_token(target.get("code"))
        if shared_auth_token:
            break

    if not shared_auth_token:
        print("[!] Indonesiana TV: Failed to obtain shared token for all channels.")
        return [], []

    all_channels, all_programmes = [], []
    with ThreadPoolExecutor(max_workers=min(4, len(targets))) as executor:
        futures = [executor.submit(fetch_epg_indonesiana_with_token, t, shared_auth_token) for t in targets]
        for fut in futures:
            ch_list, progs = fut.result()
            if ch_list:
                all_channels.extend(ch_list)
                all_programmes.extend(progs)

    return all_channels, all_programmes


# --- 4. TP CHANNEL MODULE ---
def fetch_epg_tpchannel(target):
    epg_id, offset = target["id"], target.get("utc_offset", "+0700")
    channels = [{"id": epg_id, "name": target["name"]}]
    programmes = []

    today_local = get_now_in_channel_tz(offset)
    date_param = f"{today_local.year + 543}-{today_local.strftime('%m-%d')}"
    today_str = today_local.strftime("%Y-%m-%d")

    api_url = f"https://www.tpchannel.org/tv/schedule/get-by-date?master_type_id=2&date={date_param}"
    try:
        res = HTTP_SESSION.get(api_url, headers={"X-Requested-With": "XMLHttpRequest", "Referer": target["url"]}, timeout=12)
        if res.status_code == 200:
            data = res.json()

            items = []
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                items = data.get("data", []) or data.get("result", [])

            extracted = []
            for item in items:
                t_raw = item.get("starttime") or item.get("time")
                title = item.get("title_th") or item.get("title") or item.get("program_name")

                if t_raw and title:
                    t_str = str(t_raw).strip()
                    if len(t_str) >= 5:
                        clean_time = t_str.replace(".", ":")[:5]
                        if re.match(r"^\d{2}:\d{2}$", clean_time):
                            extracted.append((clean_time, clean_text_str(title)))
                            continue

                    match = TIME_PATTERN_HM.search(t_str)
                    if match:
                        extracted.append((match.group(1).replace(".", ":").zfill(5)[:5], clean_text_str(title)))

            for i in range(len(extracted)):
                t_str, title = extracted[i]
                try:
                    start_dt = datetime.strptime(f"{today_str} {t_str}", "%Y-%m-%d %H:%M")
                    if i + 1 < len(extracted):
                        stop_dt = datetime.strptime(f"{today_str} {extracted[i+1][0]}", "%Y-%m-%d %H:%M")
                        if stop_dt <= start_dt:
                            stop_dt += timedelta(days=1)
                    else:
                        stop_dt = start_dt + timedelta(hours=1)

                    programmes.append({
                        "channel": epg_id,
                        "start": format_xmltv_date(start_dt, offset),
                        "stop": format_xmltv_date(stop_dt, offset),
                        "title": title,
                        "desc": "",
                        "lang": "th",
                    })
                except Exception:
                    continue

            print(f"[✓] TP Channel: Successfully loaded {len(programmes)} programs!")
    except Exception as e:
        print(f"[!] TP Channel Error: {e}")

    return channels, programmes


# --- 5. CLTV36 MODULE ---
def _extract_cltv36_channel_logo(soup):
    for sel in [
        ".site-branding img[src]",
        ".custom-logo-link img[src]",
        "header img[src*='logo' i]",
        "header img[src]",
    ]:
        img = soup.select_one(sel)
        if img:
            for attr in ("src", "data-src"):
                val = extract_icon_from_any(img.get(attr) or "")
                if val and "localhost" not in val:
                    return val

    og_img = soup.find("meta", property="og:image")
    if og_img and og_img.get("content"):
        val = extract_icon_from_any(og_img.get("content"))
        if val and "localhost" not in val:
            return val

    return ""


def _extract_cltv36_poster(sec):
    for a_tag in sec.select("a[href]"):
        href_clean = clean_url_str(a_tag.get("href", ""))
        if href_clean and "/wp-content/uploads/" in href_clean and "localhost" not in href_clean:
            return href_clean

    img_tag = sec.find("img")
    if img_tag:
        srcset = img_tag.get("srcset") or ""
        if srcset:
            candidates = []
            for part in srcset.split(","):
                tokens = part.strip().split()
                if tokens:
                    u = clean_url_str(tokens[0])
                    if u and "localhost" not in u:
                        w = 0
                        if len(tokens) > 1 and tokens[1].endswith("w"):
                            try:
                                w = int(tokens[1][:-1])
                            except ValueError:
                                w = 0
                        candidates.append((w, u))
            if candidates:
                candidates.sort(key=lambda x: x[0], reverse=True)
                return candidates[0][1]

        src_clean = clean_url_str(img_tag.get("src", ""))
        if src_clean and "localhost" not in src_clean:
            return src_clean

    return ""


def fetch_epg_cltv36(target):
    epg_id, offset = target["id"], target.get("utc_offset", "+0800")
    channel_logo = ""
    programmes = []

    today_local = get_now_in_channel_tz(offset)
    base_date = today_local.date()
    target_weekday_name = today_local.strftime("%A").upper()
    is_weekend = today_local.weekday() >= 5

    try:
        res = HTTP_SESSION.get(target["url"], timeout=15)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            channel_logo = _extract_cltv36_channel_logo(soup)

            retired_heading = soup.find(
                lambda tag: tag.name in ["h2", "h3"] and "RETIRED" in tag.get_text().upper()
            )

            sections = soup.select("section.elementor-section")
            if not sections:
                sections = soup.select(".elementor-widget-wrap.elementor-element-populated")

            for sec in sections:
                if retired_heading and retired_heading in sec.parents:
                    continue

                h2_tag = sec.find(["h2", "h3"], class_="elementor-heading-title")
                if not h2_tag:
                    continue

                title = clean_text_str(h2_tag.get_text(strip=True))
                if not title or "RETIRED" in title.upper() or title.upper() == "CLTV PROGRAMS":
                    continue

                poster_url = _extract_cltv36_poster(sec)

                strong_tags = sec.find_all("strong")
                schedule_blocks = []

                for strong in strong_tags:
                    s_text = strong.get_text(strip=True)
                    if TIME_PATTERN_AMPM.search(s_text) or any(
                        d in s_text.upper()
                        for d in ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY", "DAILY", "MON - FRI"]
                    ):
                        schedule_blocks.append(s_text)

                if not schedule_blocks:
                    schedule_blocks.append(sec.get_text(" ", strip=True))

                desc_text = ""
                for p in sec.find_all("p"):
                    p_str = p.get_text(strip=True)
                    if p_str and not TIME_PATTERN_AMPM.search(p_str) and not any(
                        d in p_str.upper() for d in ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"]
                    ):
                        if len(p_str) > 15 and p_str not in schedule_blocks:
                            desc_text = clean_text_str(p_str)
                            break

                for sched_str in schedule_blocks:
                    upper_sched = sched_str.upper()

                    is_match_day = False
                    if "DAILY" in upper_sched or target_weekday_name in upper_sched:
                        is_match_day = True
                    elif ("MONDAY - FRIDAY" in upper_sched or "MON - FRI" in upper_sched or "MONDAY – FRIDAY" in upper_sched) and not is_weekend:
                        is_match_day = True
                    elif ("MONDAY - SATURDAY" in upper_sched or "MONDAY – SATURDAY" in upper_sched) and target_weekday_name != "SUNDAY":
                        is_match_day = True
                    elif not any(day in upper_sched for day in ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"]):
                        is_match_day = True

                    if not is_match_day:
                        continue

                    norm_sched = sched_str.replace("–", "-")
                    norm_sched = re.sub(
                        r"(\b\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2}\s*(AM|PM))",
                        r"\1 \3 - \2",
                        norm_sched,
                        flags=re.IGNORECASE,
                    )

                    time_matches = TIME_PATTERN_AMPM.findall(norm_sched.replace("NN", "PM").replace("nn", "pm"))

                    for idx in range(0, len(time_matches) - 1, 2):
                        try:
                            start_str = time_matches[idx].upper().replace(" ", "")
                            stop_str = time_matches[idx + 1].upper().replace(" ", "")

                            start_time = datetime.strptime(start_str.zfill(7), "%I:%M%p").time()
                            stop_time = datetime.strptime(stop_str.zfill(7), "%I:%M%p").time()

                            start_dt = datetime.combine(base_date, start_time).replace(tzinfo=today_local.tzinfo)
                            stop_dt = datetime.combine(base_date, stop_time).replace(tzinfo=today_local.tzinfo)

                            if stop_dt <= start_dt:
                                stop_dt += timedelta(days=1)

                            prog_entry = {
                                "channel": epg_id,
                                "start": format_xmltv_date(start_dt, offset),
                                "stop": format_xmltv_date(stop_dt, offset),
                                "title": title,
                                "desc": desc_text,
                                "icon": poster_url,
                                "lang": "en",
                            }

                            if prog_entry not in programmes:
                                programmes.append(prog_entry)
                        except Exception:
                            pass

            programmes.sort(key=lambda x: x["start"])
            print(f"[✓] CLTV36: Successfully loaded {len(programmes)} programs for today ({target_weekday_name})!")
    except Exception as e:
        print(f"[!] CLTV36 Error: {e}")

    channels = [{"id": epg_id, "name": target["name"], "icon": channel_logo}]
    return channels, programmes


# --- 6. MNC VISION MODULE ---
def get_mnc_channel_options():
    url = "https://www.mncvision.id/schedule/table"
    EXCLUDED_MNC_IDS = {
        "12", "13", "14", "19", "20", "22", "23", "78", "80", "81", "82", "83", "84", "87", "89", "97", "103", "106", "107",
        "110", "113", "115", "116", "118", "160", "161", "167", "205", "240", "248", "330", "331", "352", "355", "357", "406",
        "409", "415", "417", "418", "419", "427", "428", "430", "431", "432", "433", "434", "437", "438", "446", "447",
    }

    channels = []
    try:
        res = HTTP_SESSION.get(url, timeout=25)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            select = soup.find("select", {"name": "fchannel"}) or soup.find("select", {"id": "fchannel"})
            if select:
                for opt in select.find_all("option"):
                    val = opt.get("value")
                    raw_name = clean_text_str(opt.get_text())
                    if val and str(val) != "0" and raw_name and "Pilih Channel" not in raw_name and "Toggle" not in raw_name:
                        if str(val) in EXCLUDED_MNC_IDS:
                            continue

                        clean_channel_name = re.sub(r"\s*-\s*\[.*?\]", "", raw_name).strip()
                        slug = re.sub(r"[-\s]+", "-", re.sub(r"[^\w\s-]", "", clean_channel_name.lower().strip()))
                        slug_id = f"MNC_{slug}_{val}.id"

                        channels.append({
                            "code": str(val),
                            "clean_name": clean_channel_name,
                            "slug_id": slug_id,
                        })
    except Exception as e:
        print(f"[!] Failed to retrieve the channel list: {e}")
    return channels


def fetch_single_mnc_epg(ch_info):
    today_str = get_now_in_channel_tz("+0700").strftime("%Y-%m-%d")
    mnc_headers = {
        "User-Agent": HEADERS["User-Agent"],
        "Origin": "https://www.mncvision.id",
        "Referer": "https://www.mncvision.id/schedule/table",
    }

    programmes = []
    seen_prog_keys = set()
    ch_id = ch_info["slug_id"]
    ch_name = ch_info["clean_name"]

    local_session = requests.Session()
    local_session.headers.update(HEADERS)

    for startno in [0, 50, 100]:
        try:
            if startno == 0:
                post_url = "https://www.mncvision.id/schedule/table"
                payload = {
                    "search_model": "channel",
                    "af0rmelement": "aformelement",
                    "fdate": today_str,
                    "fchannel": ch_info["code"],
                    "submit": "Cari",
                }
                res = HTTP_SESSION.post(post_url, data=payload, headers=mnc_headers, timeout=35)
            else:
                get_url = f"https://www.mncvision.id/schedule/table/startno/{startno}"
                res = local_session.get(get_url, headers=mnc_headers, timeout=25)

            if res.status_code != 200:
                break

            soup = BeautifulSoup(res.text, "html.parser")
            table = soup.find("table", class_=re.compile(r"table", re.I)) or soup.find("table")

            if not table:
                break

            rows = table.find_all("tr")[1:]
            if not rows:
                break

            for row in rows:
                cols = row.find_all(["td", "th"])
                if len(cols) >= 2:
                    time_str = clean_text_str(cols[0].get_text())
                    title_str = clean_text_str(cols[1].get_text())
                    duration_str = clean_text_str(cols[2].get_text()) if len(cols) >= 3 else ""

                    if time_str and title_str and "Toggle navigation" not in title_str and "Jadwal Tidak Ditemukan" not in title_str:
                        match = TIME_PATTERN_HM.search(time_str)
                        if match:
                            t_clean = match.group(1).replace(".", ":").zfill(5)[:5]
                            try:
                                start_dt = datetime.strptime(f"{today_str} {t_clean}", "%Y-%m-%d %H:%M")
                                stop_dt = start_dt + timedelta(hours=1)
                                dur_match = re.search(r"(\d{2}):(\d{2})", duration_str)
                                if dur_match:
                                    h_dur, m_dur = int(dur_match.group(1)), int(dur_match.group(2))
                                    stop_dt = start_dt + timedelta(hours=h_dur, minutes=m_dur)
                                    if stop_dt <= start_dt:
                                        stop_dt += timedelta(days=1)

                                start_formatted = format_xmltv_date(start_dt, "+0700")
                                unique_key = (start_formatted, title_str)

                                if unique_key not in seen_prog_keys:
                                    seen_prog_keys.add(unique_key)
                                    programmes.append({
                                        "channel": ch_id,
                                        "start": start_formatted,
                                        "stop": format_xmltv_date(stop_dt, "+0700"),
                                        "title": title_str,
                                        "desc": "",
                                        "lang": "id",
                                    })
                            except Exception:
                                continue

            if len(rows) < 50:
                break

        except Exception:
            break

    if programmes:
        print(f"[✓] MNC Vision [{ch_name}]: Successfully loaded {len(programmes)} programs.")
        return [{"id": ch_id, "name": ch_name}], programmes

    return [], []


def fetch_all_mncvision_parallel():
    channels_list = get_mnc_channel_options()
    if not channels_list:
        return [], []

    print(f"[*] Starting parallel EPG extraction for {len(channels_list)} MNC Vision channels...")
    all_channels, all_programmes = [], []
    with ThreadPoolExecutor(max_workers=20) as executor:
        results = executor.map(fetch_single_mnc_epg, channels_list)
        for ch_list, progs in results:
            if progs:
                all_channels.extend(ch_list)
                all_programmes.extend(progs)

    print(f"[✓] MNC Vision: Successfully extracted {len(all_channels)} active channels & {len(all_programmes)} programs!")
    return all_channels, all_programmes


# --- 7. QAZAQSTAN NETWORK MODULE ---
def fetch_epg_qazaqstan(target):
    epg_id, offset = target["id"], target.get("utc_offset", "+0500")
    channels = [{"id": epg_id, "name": target["name"]}]
    programmes = []
    today_str = get_now_in_channel_tz(offset).strftime("%Y-%m-%d")
    base_url = target["url"].rstrip("/")
    direct_url = f"{base_url}/{today_str}" if not base_url.endswith(today_str) else base_url

    for url in [direct_url, f"https://iptv-playlist.sulthan-pamenan.workers.dev/?url={quote(direct_url, safe='')}"]:
        try:
            res = HTTP_SESSION.get(url, timeout=15)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, "html.parser")

            items = soup.select("div.flex.items-center.justify-between.w-full, .program-item")

            raw_progs = []
            for item in items:
                time_elem = item.select_one(".font-bold.text-h5, [class*='text-h5'], [class*='font-bold']")
                time_text = time_elem.get_text(strip=True) if time_elem else ""

                match = TIME_PATTERN_HM.search(time_text) or TIME_PATTERN_HM.search(item.get_text(" ", strip=True))
                if match:
                    t_str = match.group(1).replace(".", ":").zfill(5)[:5]

                    category_elem = item.select_one("div.text-xs, [class*='text-xs']")
                    title_elem = item.select_one(".program-title, [class*='program-title']")

                    cat_text = clean_text_str(category_elem.get_text(strip=True)) if category_elem else ""
                    title_text = clean_text_str(title_elem.get_text(strip=True)) if title_elem else ""

                    genre_keywords = [
                        "деректі фильм", "деректі фильмдер", "телехикая", "телехикаялар", "бағдарлама", "бағдарламалар",
                        "мультхикая", "мультхикаялар", "мегажоба", "мегажобалар", "көркем фильм", "көркем фильмдер",
                        "ақпараттық-саяси бағдарлама",
                    ]

                    if any(kw in title_text.lower() for kw in genre_keywords) and not any(kw in cat_text.lower() for kw in genre_keywords):
                        category = title_text
                        raw_title = cat_text
                    else:
                        category = cat_text
                        raw_title = title_text

                    if not raw_title:
                        bold_elems = item.select("div.font-bold, [class*='font-bold']")
                        for b in bold_elems:
                            b_text = b.get_text(strip=True)
                            if b_text and not TIME_PATTERN_HM.search(b_text) and b_text != category:
                                raw_title = b_text
                                break

                    clean_title = re.sub(r"^[–\-\:\s\.\,]+|[–\-\:\s\.\,]+$", "", raw_title)
                    clean_title = re.sub(r"(онлайн көру|live|эфирде)", "", clean_title, flags=re.IGNORECASE)
                    clean_title = clean_text_str(clean_title)

                    if clean_title and len(clean_title) >= 2 and not TIME_PATTERN_HM.match(clean_title):
                        if not any(r["start_str"] == t_str and r["title"] == clean_title for r in raw_progs):
                            desc_text = category if (category and category != clean_title) else ""
                            raw_progs.append({
                                "start_str": t_str,
                                "title": clean_title,
                                "desc": desc_text,
                            })

            if raw_progs:
                for i in range(len(raw_progs)):
                    curr = raw_progs[i]
                    t_str = curr["start_str"]
                    try:
                        start_dt = datetime.strptime(f"{today_str} {t_str}", "%Y-%m-%d %H:%M")
                        if i + 1 < len(raw_progs):
                            stop_dt = datetime.strptime(f"{today_str} {raw_progs[i+1]['start_str']}", "%Y-%m-%d %H:%M")
                            if stop_dt <= start_dt:
                                stop_dt += timedelta(days=1)
                        else:
                            stop_dt = start_dt + timedelta(hours=1)

                        programmes.append({
                            "channel": epg_id,
                            "start": format_xmltv_date(start_dt, offset),
                            "stop": format_xmltv_date(stop_dt, offset),
                            "title": curr["title"],
                            "desc": curr["desc"],
                            "lang": "kk",
                        })
                    except Exception:
                        continue
                print(f"[✓] {target['name']}: Successfully loaded {len(programmes)} programs.")
                break
        except Exception:
            continue

    return channels, programmes


# --- 8. RED BULL TV MODULE ---
def fetch_single_redbull_channel(t):
    api_url = f"https://tv-api.redbull.com/guides/v5.1/rbtv/id_ID/id/{t['rrn']}"
    programmes = []
    wib_tz = timezone(timedelta(hours=7))

    try:
        res = HTTP_SESSION.get(api_url, timeout=10)
        if res.status_code == 200:
            data = res.json()
            cards = data.get("cards", [])

            for item in cards:
                title = item.get("title")
                desc = item.get("short_description") or item.get("long_description") or ""
                start_iso = item.get("start_time")
                end_iso = item.get("end_time")

                if start_iso and title:
                    start_dt = datetime.fromisoformat(str(start_iso).replace("Z", "+00:00")).astimezone(wib_tz)

                    if end_iso:
                        end_dt = datetime.fromisoformat(str(end_iso).replace("Z", "+00:00")).astimezone(wib_tz)
                    else:
                        end_dt = start_dt + timedelta(hours=1)

                    programmes.append({
                        "channel": t["id"],
                        "start": format_xmltv_date(start_dt, "+0700"),
                        "stop": format_xmltv_date(end_dt, "+0700"),
                        "title": clean_text_str(title),
                        "desc": clean_text_str(desc),
                        "lang": "en",
                    })

            print(f"[✓] Red Bull TV [{t['name']}]: Successfully loaded {len(programmes)} programs.")
    except Exception as e:
        print(f"[!] Red Bull TV Error [{t['name']}]: {e}")

    return {"id": t["id"], "name": t["name"]}, programmes


def fetch_epg_redbull_all(targets):
    if not targets:
        return [], []
    channels = []
    all_programmes = []
    with ThreadPoolExecutor(max_workers=min(9, len(targets))) as executor:
        results = executor.map(fetch_single_redbull_channel, targets)
        for ch_info, progs in results:
            if progs:
                channels.append(ch_info)
                all_programmes.extend(progs)
    return channels, all_programmes


# --- 9. KBS WORLD MODULE ---
def fetch_epg_kbsworld(target):
    epg_id = target["id"]
    channels = [{"id": epg_id, "name": target["name"]}]
    programmes = []

    start_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    end_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

    url = "https://kbsworld.kbs.co.kr/schedule/down_schedule_db.php"
    headers = {
        "User-Agent": HEADERS["User-Agent"],
        "Referer": "https://kbsworld.kbs.co.kr/schedule/list.php",
    }
    params = {
        "wlang": "e",
        "down_time_add": "-2",
        "start_date": start_date,
        "end_date": end_date,
    }

    session = requests.Session()

    try:
        session.get("https://kbsworld.kbs.co.kr/", headers=headers, verify=False, timeout=10)
        response = session.get(url, headers=headers, params=params, verify=False, timeout=20)
        response.raise_for_status()

        dfs = pd.read_html(io.StringIO(response.text))
        if not dfs or len(dfs[0]) == 0:
            print("[!] KBS World: Table data is empty or failed to parse.")
            return channels, programmes

        df = dfs[0]
        for row in df.itertuples(index=False):
            try:
                date_str = str(row.Date).strip()
                time_str = str(getattr(row, "_1")).strip()

                title_base = str(getattr(row, "Title", "")).strip()
                if not title_base or title_base.lower() == "nan":
                    continue

                ep_info = ""
                for col_name in df.columns:
                    col_str = str(col_name).lower()
                    if col_str in ["title", "synop", "duration", "date", "_1"]:
                        continue

                    if any(k in col_str for k in ["sub", "ep", "episode", "number"]) or col_str == "no":
                        val = str(getattr(row, str(col_name), "")).strip()
                        if val and val.lower() not in ["nan", "none", ""]:
                            if not ep_info:
                                ep_info = val
                            elif val not in ep_info:
                                ep_info += f" {val}"

                if ep_info:
                    ep_info = re.sub(r"(\d+)\.0\b", r"\1", ep_info)

                if ep_info and ep_info.lower() not in title_base.lower():
                    if not ep_info.lower().startswith("ep"):
                        title = f"{title_base} Ep.{ep_info}"
                    else:
                        title = f"{title_base} {ep_info}"
                else:
                    title = title_base

                synop_val = getattr(row, "Synop", "No description")
                synop = str(synop_val).strip() if pd.notna(synop_val) else "No description"

                duration_val = getattr(row, "Duration", 30)
                duration_min = int(duration_val) if pd.notna(duration_val) else 30

                dt_start = datetime.strptime(f"{date_str} {time_str}", "%Y%m%d %H:%M")
                dt_end = dt_start + timedelta(minutes=duration_min)

                target_offset = target.get("utc_offset", "+0700")
                start_formatted = format_xmltv_date(dt_start, target_offset)
                stop_formatted = format_xmltv_date(dt_end, target_offset)

                programmes.append({
                    "channel": epg_id,
                    "start": start_formatted,
                    "stop": stop_formatted,
                    "title": title,
                    "desc": synop,
                    "lang": "en",
                })
            except Exception:
                continue

        print(f"[✓] KBS World: Successfully loaded {len(programmes)} programs.")
    except Exception as e:
        print(f"[!] KBS World Error: {e}")

    return channels, programmes


# --- ROUTER & EXECUTION ---
def process_single_target(target):
    t_id = target.get("id", "")
    if "rrn" in target:
        return fetch_single_redbull_channel(target)
    if t_id == "TPChannel.th":
        return fetch_epg_tpchannel(target)
    if t_id == "CLTV36.ph":
        return fetch_epg_cltv36(target)
    if t_id == "KBSWorld.id":
        return fetch_epg_kbsworld(target)
    if t_id.startswith("Indonesiana_"):
        return fetch_epg_indonesiana(target)
    if t_id.endswith(".kz"):
        return fetch_epg_qazaqstan(target)
    return [], []


def _append_results(all_channels, all_programmes, ch_list, progs):
    if ch_list:
        all_channels.extend(ch_list)
    if progs:
        all_programmes.extend(progs)


def _write_channels_xml(tv_elem, all_channels):
    seen_channels = set()
    for ch in all_channels:
        ch_id = ch.get("id")
        if not ch_id or ch_id in seen_channels:
            continue
        seen_channels.add(ch_id)
        c_elem = ET.SubElement(tv_elem, "channel", id=ch_id)
        ET.SubElement(c_elem, "display-name").text = clean_text_str(ch.get("name", ch_id))
        ch_icon_url = extract_icon_from_any(ch.get("icon", ""))
        if ch_icon_url:
            ET.SubElement(c_elem, "icon", src=ch_icon_url)
    return seen_channels


def _write_programmes_xml(tv_elem, all_programmes):
    now_utc = datetime.now(timezone.utc)
    cutoff_utc = now_utc - timedelta(hours=12)
    seen_programmes = set()

    for p in all_programmes:
        try:
            stop_str_dt = str(p["stop"]).split(" ")[0]
            stop_dt = datetime.strptime(stop_str_dt, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
            if stop_dt < cutoff_utc:
                continue
        except Exception:
            pass

        title_val = str(p["title"]) if not isinstance(p["title"], (set, list, dict)) else " ".join(p["title"])
        cleaned_title = html.unescape(clean_text_str(title_val))
        if not cleaned_title:
            continue

        dedup_key = (p["channel"], p["start"], cleaned_title.lower())
        if dedup_key in seen_programmes:
            continue
        seen_programmes.add(dedup_key)

        lang = p.get("lang", "en")
        p_elem = ET.SubElement(
            tv_elem,
            "programme",
            {"start": p["start"], "stop": p["stop"], "channel": p["channel"]},
        )
        ET.SubElement(p_elem, "title", lang=lang).text = cleaned_title

        if p.get("subtitle") and str(p["subtitle"]).strip():
            ET.SubElement(p_elem, "sub-title", lang=lang).text = html.unescape(clean_xml_text(p["subtitle"]))

        if p.get("desc") and str(p["desc"]).strip():
            desc_val = str(p["desc"]) if not isinstance(p["desc"], (set, list, dict)) else " ".join(p["desc"])
            cleaned_desc = html.unescape(clean_text_str(desc_val))
            if cleaned_desc:
                ET.SubElement(p_elem, "desc", lang=lang).text = cleaned_desc

        if p.get("category") and str(p["category"]).strip() and p.get("category") != "General":
            cat_val = str(p["category"])
            ET.SubElement(p_elem, "category", lang=lang).text = html.unescape(clean_text_str(cat_val))

        prog_icon_url = extract_icon_from_any(p.get("icon", ""))
        if prog_icon_url:
            ET.SubElement(p_elem, "icon", src=prog_icon_url)

    return seen_programmes


def generate_xmltv():
    print("=" * 60)
    print("[*] Starting EPG XMLTV Generation")
    print("=" * 60)

    tv_elem = ET.Element("tv", {"generator-info-name": "Universal Master EPG Generator"})
    all_channels, all_programmes = [], []

    # 1. Tivie.id (Parallel)
    tivie_chs, tivie_progs = fetch_all_tivie_parallel()
    _append_results(all_channels, all_programmes, tivie_chs, tivie_progs)

    # 2. Dens.TV (Parallel)
    dens_chs, dens_progs = fetch_all_dens_parallel()
    _append_results(all_channels, all_programmes, dens_chs, dens_progs)

    # 3. Red Bull TV (Parallel)
    redbull_targets = [t for t in EPG_TARGET_SOURCES if "rrn" in t]
    rb_chs, rb_progs = fetch_epg_redbull_all(redbull_targets)
    _append_results(all_channels, all_programmes, rb_chs, rb_progs)

    # 4. MNC Vision (Parallel)
    mnc_chs, mnc_progs = fetch_all_mncvision_parallel()
    _append_results(all_channels, all_programmes, mnc_chs, mnc_progs)

    # 5. Other Sources via Router (TP Channel, CLTV36, KBS World, Qazaqstan Network)
    other_targets = [
        t for t in EPG_TARGET_SOURCES
        if "rrn" not in t and not t["id"].startswith("Indonesiana_")
    ]
    if other_targets:
        with ThreadPoolExecutor(max_workers=min(9, len(other_targets))) as executor:
            for ch_list, progs in executor.map(process_single_target, other_targets):
                _append_results(all_channels, all_programmes, ch_list, progs)

    # 6. Indonesiana TV (Shared Token + Parallel Fetch)
    indonesiana_targets = [t for t in EPG_TARGET_SOURCES if t["id"].startswith("Indonesiana_")]
    indo_chs, indo_progs = fetch_all_indonesiana(indonesiana_targets)
    _append_results(all_channels, all_programmes, indo_chs, indo_progs)

    # 7 & 8. Serialize Channels & Programmes to XMLTV
    seen_channels = _write_channels_xml(tv_elem, all_channels)
    seen_programmes = _write_programmes_xml(tv_elem, all_programmes)

    try:
        ET.indent(tv_elem, space="  ")
    except AttributeError:
        pass

    ET.ElementTree(tv_elem).write("epg.xml", encoding="utf-8", xml_declaration=True)
    print("=" * 60)
    print(f"[SUCCESS] Successfully generated `epg.xml` with {len(seen_channels)} total channels & {len(seen_programmes)} programs!")
    print("=" * 60)


if __name__ == "__main__":
    generate_xmltv()
