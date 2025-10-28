#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse, json, sys, time
from pathlib import Path
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/127.0.0.0 Safari/537.36"
)
TIMEOUT_MS = 60000  # 60s

def wait_past_cloudflare(page, max_wait_ms=45000):
    """Wait until Cloudflare 'Just a moment...' is gone."""
    start = time.time()
    while (time.time() - start) * 1000 < max_wait_ms:
        title = (page.title() or "").strip().lower()
        if title and title != "just a moment...":
            return True
        page.wait_for_timeout(1500)
    return (page.title() or "").strip().lower() != "just a moment..."

def get_html_after_ready(page):
    """
    Heuristic readiness:
    - wait for DOM + CF to clear
    - if details aren't detected, let you complete any on-page challenge and press Enter
    """
    page.wait_for_load_state("domcontentloaded", timeout=TIMEOUT_MS)
    wait_past_cloudflare(page, max_wait_ms=45000)

    try:
        page.wait_for_selector("dl dt", timeout=5000)
    except Exception:
        print("\nIf the browser shows a challenge, complete it there.")
        input("When the cert details are visible, press ENTER here to continue… ")

    page.wait_for_timeout(800)
    return page.content()

def extract_all(soup: BeautifulSoup) -> dict:
    data = {}

    # Title / headings
    if soup.title:
        data["page_title"] = soup.title.get_text(" ", strip=True)
    h1 = soup.find("h1")
    if h1:
        data["h1"] = h1.get_text(" ", strip=True)
    h2 = soup.find("h2")
    if h2:
        data["h2"] = h2.get_text(" ", strip=True)

    # JSON-LD
    json_ld = []
    for s in soup.find_all("script", type="application/ld+json"):
        try:
            import json as _json
            obj = _json.loads(s.string or "")
            if isinstance(obj, list):
                json_ld.extend(obj)
            elif isinstance(obj, dict):
                json_ld.append(obj)
        except Exception:
            pass
    if json_ld:
        data["json_ld"] = json_ld

    # Definition lists (common on detail pages)
    details = {}
    for dl in soup.find_all("dl"):
        dts = dl.find_all("dt")
        dds = dl.find_all("dd")
        if len(dts) and len(dds) and len(dts) == len(dds):
            for dt, dd in zip(dts, dds):
                k = dt.get_text(" ", strip=True)
                v = dd.get_text(" ", strip=True)
                if k and v:
                    details[k] = v
    if details:
        data["details"] = details

    # Simple 2-col tables as fallback
    table_fields = {}
    for table in soup.find_all("table"):
        for tr in table.find_all("tr"):
            tds = tr.find_all(["td", "th"])
            if len(tds) == 2:
                k = tds[0].get_text(" ", strip=True)
                v = tds[1].get_text(" ", strip=True)
                if k and v:
                    table_fields[k] = v
    if table_fields:
        data["table_fields"] = table_fields

    # Images
    imgs = []
    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src")
        if src and not src.startswith("data:"):
            alt = img.get("alt") or ""
            imgs.append({"src": src, "alt": alt})
    if imgs:
        data["images"] = imgs

    return data

def lookup_cert_gui(cert: str, debug: bool=False) -> dict:
    result = {"cert": cert, "attempts": []}
    url = f"https://www.cgccomics.com/certlookup/{cert}/"

    with sync_playwright() as p:
        # Headed browser helps pass Cloudflare / lets you click if needed
        browser = p.chromium.launch(headless=False, slow_mo=100)
        context = browser.new_context(
            user_agent=DEFAULT_UA,
            ignore_https_errors=True,
            viewport={"width": 1366, "height": 820},
            locale="en-US",
        )
        page = context.new_page()

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=TIMEOUT_MS)
            html = get_html_after_ready(page)

            if debug:
                Path("cgc_debug").mkdir(exist_ok=True)
                Path("cgc_debug/final.html").write_text(html, encoding="utf-8")

            soup = BeautifulSoup(html, "lxml")
            data = extract_all(soup)

            attempt = {
                "via": "headed_direct",
                "url": url,
                "status": "ok" if data else "no_data",
                "data_found": bool(data)
            }
            if data:
                attempt["data"] = data
                result["best_url"] = url
                result["data"] = data
            result["attempts"].append(attempt)
        finally:
            try:
                browser.close()
            except Exception:
                pass

    if "data" not in result:
        result["error"] = "Could not retrieve or parse details."
    return result

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cert", nargs="?", help="CGC certification number (digits)")
    ap.add_argument("--debug", action="store_true", help="Save HTML to ./cgc_debug/final.html")
    args = ap.parse_args()

    cert = args.cert or input("Enter CGC certification number: ").strip()
    if not cert:
        print("No cert provided."); sys.exit(1)

    out = lookup_cert_gui(cert, debug=args.debug)
    print(json.dumps(out, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
