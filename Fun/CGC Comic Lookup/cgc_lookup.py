#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
cgc_lookup.py — Look up CGC certification details and print all available data.

Usage:
  python cgc_lookup.py               # interactive prompt
  python cgc_lookup.py 2808050001    # direct cert as arg
  python cgc_lookup.py 2808050001 --out-json result.json --out-csv result.csv

If requests are blocked by CGC's WAF, the script will automatically try a headless
browser (Playwright) if available.
"""

import argparse
import json
import sys
import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from slugify import slugify

PLAYWRIGHT_AVAILABLE = False
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except Exception:
    PLAYWRIGHT_AVAILABLE = False

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/127.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Cache-Control": "no-cache",
}

# Candidate lookup URLs (CGC hosts multiple verticals)
URL_PATTERNS = [
    # Comics/Magazines:
    "https://www.cgccomics.com/certlookup/{cert}/",
    # Cards:
    "https://www.cgccards.com/certlookup/{cert}/",
    # (Video Games/Home Video often use a form page; you can add more patterns if needed)
]

TIMEOUT = 30


def fetch_requests(url: str) -> str | None:
    """Fetch a page with requests. Returns text or None if blocked/error."""
    try:
        with requests.Session() as s:
            s.headers.update(DEFAULT_HEADERS)
            r = s.get(url, timeout=TIMEOUT)
            if r.status_code == 200 and r.text:
                return r.text
            # Some CGC responses use 403 (WAF) or 200 with "Item cannot be found".
            return None
    except requests.RequestException:
        return None


def fetch_playwright(url: str) -> str | None:
    """Fetch a page with Playwright headless browser. Returns HTML or None."""
    if not PLAYWRIGHT_AVAILABLE:
        return None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(user_agent=DEFAULT_HEADERS["User-Agent"])
            page = context.new_page()
            page.set_default_timeout(TIMEOUT * 1000)

            # Go to URL and wait for network to be idle-ish.
            page.goto(url, wait_until="domcontentloaded")
            # Try to allow images/JS to settle a bit
            page.wait_for_timeout(700)

            content = page.content()
            browser.close()
            return content
    except Exception:
        return None


def extract_key_values(soup: BeautifulSoup) -> dict:
    """Extract as many labeled fields as possible from common page structures."""
    data = {}

    # 1) JSON-LD blocks (often contain Product / item details)
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            obj = json.loads(script.string or "")
            # Could be a dict or list of dicts
            if isinstance(obj, dict):
                data.setdefault("json_ld", []).append(obj)
            elif isinstance(obj, list):
                data.setdefault("json_ld", []).extend(obj)
        except Exception:
            pass

    # 2) OpenGraph / Twitter cards (titles, descriptions, images)
    meta = {}
    for tag in soup.find_all("meta"):
        prop = tag.get("property") or tag.get("name")
        if prop and (prop.startswith("og:") or prop.startswith("twitter:")):
            meta[prop] = tag.get("content")
    if meta:
        data["meta"] = meta

    # 3) Look for common definition lists (dt/dd) that many detail pages use
    details = {}
    for dl in soup.find_all("dl"):
        dts = dl.find_all("dt")
        dds = dl.find_all("dd")
        if len(dts) and len(dds) and len(dts) == len(dds):
            for dt, dd in zip(dts, dds):
                k = " ".join(dt.get_text(" ", strip=True).split())
                v = " ".join(dd.get_text(" ", strip=True).split())
                if k and v:
                    details[k] = v
    if details:
        data["details"] = details

    # 4) Tables with two columns (label/value)
    table_fields = {}
    for table in soup.find_all("table"):
        for tr in table.find_all("tr"):
            tds = tr.find_all(["td", "th"])
            if len(tds) == 2:
                k = " ".join(tds[0].get_text(" ", strip=True).split())
                v = " ".join(tds[1].get_text(" ", strip=True).split())
                if k and v:
                    table_fields[k] = v
    if table_fields:
        data["table_fields"] = table_fields

    # 5) Page title and any prominent H1/H2 text (often contains book title/grade)
    title = soup.find("title")
    if title:
        data["page_title"] = " ".join(title.get_text(" ", strip=True).split())
    h1 = soup.find("h1")
    if h1:
        data["h1"] = " ".join(h1.get_text(" ", strip=True).split())
    h2 = soup.find("h2")
    if h2:
        data["h2"] = " ".join(h2.get_text(" ", strip=True).split())

    # 6) Images — capture likely cover/front/back images
    images = []
    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src")
        alt = img.get("alt") or ""
        if src and not src.startswith("data:"):
            images.append({"src": src, "alt": alt})
    if images:
        data["images"] = images

    # 7) Fallback: grab any “This item cannot be found” error text
    body_text = soup.get_text(" ", strip=True)
    if "cannot be found" in body_text.lower():
        data.setdefault("messages", []).append("Item cannot be found (as rendered).")

    return data


def lookup_cert(cert: str) -> dict:
    """Try multiple endpoints; return first rich result."""
    result = {"cert": cert, "attempts": []}

    for pattern in URL_PATTERNS:
        url = pattern.format(cert=cert)
        attempt = {"url": url, "method": "requests", "status": "skipped", "data_found": False}
        html = fetch_requests(url)
        if not html:
            attempt["status"] = "blocked_or_empty"
            # Try Playwright if available
            if PLAYWRIGHT_AVAILABLE:
                attempt_pw = {"url": url, "method": "playwright", "status": "skipped", "data_found": False}
                html_pw = fetch_playwright(url)
                if html_pw:
                    soup = BeautifulSoup(html_pw, "lxml")
                    data = extract_key_values(soup)
                    if data:
                        attempt_pw["status"] = "ok"
                        attempt_pw["data_found"] = True
                        attempt_pw["data"] = data
                        result["attempts"].append(attempt)
                        result["attempts"].append(attempt_pw)
                        result["best_url"] = url
                        result["data"] = data
                        return result
                attempt_pw["status"] = "blocked_or_empty"
                result["attempts"].append(attempt)
                result["attempts"].append(attempt_pw)
                continue
            else:
                result["attempts"].append(attempt)
                continue
        else:
            attempt["status"] = "ok"
            soup = BeautifulSoup(html, "lxml")
            data = extract_key_values(soup)
            attempt["data_found"] = bool(data)
            attempt["data"] = data
            result["attempts"].append(attempt)
            if data:
                result["best_url"] = url
                result["data"] = data
                return result

    # If we got here, we failed to extract useful data
    result["error"] = "Could not retrieve or parse details for this certification."
    return result


def flatten_for_csv(data: dict) -> dict:
    """
    Flatten the rich structure to a 1-row dict for CSV convenience.
    We keep the richest bits as JSON strings in columns.
    """
    row = {
        "cert": data.get("cert", ""),
        "best_url": data.get("best_url", ""),
        "page_title": data.get("data", {}).get("page_title", ""),
        "h1": data.get("data", {}).get("h1", ""),
        "h2": data.get("data", {}).get("h2", ""),
        "details_json": json.dumps(data.get("data", {}).get("details", {}), ensure_ascii=False),
        "table_fields_json": json.dumps(data.get("data", {}).get("table_fields", {}), ensure_ascii=False),
        "meta_json": json.dumps(data.get("data", {}).get("meta", {}), ensure_ascii=False),
        "json_ld": json.dumps(data.get("data", {}).get("json_ld", []), ensure_ascii=False),
        "images_json": json.dumps(data.get("data", {}).get("images", []), ensure_ascii=False),
    }
    return row


def main():
    ap = argparse.ArgumentParser(description="Look up CGC certification details.")
    ap.add_argument("cert", nargs="?", help="CGC certification number, e.g., 2808050001")
    ap.add_argument("--out-json", dest="out_json", help="Write full results to this JSON file")
    ap.add_argument("--out-csv", dest="out_csv", help="Append a CSV row with flattened fields")
    args = ap.parse_args()

    cert = args.cert
    if not cert:
        try:
            cert = input("Enter CGC certification number: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nCanceled.")
            sys.exit(1)

    if not cert.isdigit():
        print("Certification numbers are typically numeric. Continuing anyway...")

    result = lookup_cert(cert)

    # Print to stdout (pretty JSON)
    print(json.dumps(result, indent=2, ensure_ascii=False))

    # Optionally write JSON
    if args.out_json:
        Path(args.out_json).write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nSaved JSON → {args.out_json}")

    # Optionally write CSV
    if args.out_csv:
        import csv
        row = flatten_for_csv(result)
        file_exists = Path(args.out_csv).exists()
        with open(args.out_csv, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(row.keys()))
            if not file_exists:
                writer.writeheader()
            writer.writerow(row)
        print(f"Appended CSV row → {args.out_csv}")


if __name__ == "__main__":
    main()
