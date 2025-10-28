#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse, json, sys
from pathlib import Path
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup

PLAYWRIGHT_AVAILABLE = False
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    PLAYWRIGHT_AVAILABLE = True
except Exception:
    PLAYWRIGHT_AVAILABLE = False

DEFAULT_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/127.0.0.0 Safari/537.36"),
    "Accept-Language": "en-US,en;q=0.9",
}

VERIFY_PORTAL = "https://www.cgcgrading.com/verify"
# Tiles we’ll try in order (most common first)
VERIFY_TILES = [
    # (human label substring, url hostname we expect after clicking)
    ("Comics", "www.cgccomics.com"),
    ("Cards", "www.cgccards.com"),
    ("Video Game", "www.cgcvideogames.com"),
    ("Home Video", "www.cgchomevideo.com"),
]

DIRECT_URL_PATTERNS = [
    "https://www.cgccomics.com/certlookup/{cert}/",
    "https://www.cgccards.com/certlookup/{cert}/",
    "https://www.cgcvideogames.com/cert-lookup?cert={cert}",
    "https://www.cgchomevideo.com/en-US/cert-lookup?cert={cert}",
]

TIMEOUT_MS = 30000


def extract_key_values(soup: BeautifulSoup) -> dict:
    data = {}
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            obj = json.loads(script.string or "")
            if isinstance(obj, dict):
                data.setdefault("json_ld", []).append(obj)
            elif isinstance(obj, list):
                data.setdefault("json_ld", []).extend(obj)
        except Exception:
            pass
    meta = {}
    for tag in soup.find_all("meta"):
        prop = tag.get("property") or tag.get("name")
        if prop and (prop.startswith("og:") or prop.startswith("twitter:")):
            meta[prop] = tag.get("content")
    if meta:
        data["meta"] = meta
    details = {}
    for dl in soup.find_all("dl"):
        dts, dds = dl.find_all("dt"), dl.find_all("dd")
        if len(dts) and len(dds) and len(dts) == len(dds):
            for dt, dd in zip(dts, dds):
                k = dt.get_text(" ", strip=True)
                v = dd.get_text(" ", strip=True)
                if k and v:
                    details[k] = v
    if details:
        data["details"] = details
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
    title = soup.find("title")
    if title:
        data["page_title"] = title.get_text(" ", strip=True)
    for tag in ("h1", "h2"):
        el = soup.find(tag)
        if el:
            data[tag] = el.get_text(" ", strip=True)
    images = []
    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src")
        alt = img.get("alt") or ""
        if src and not src.startswith("data:"):
            images.append({"src": src, "alt": alt})
    if images:
        data["images"] = images
    return data


def fetch_requests(url: str) -> str | None:
    try:
        r = requests.get(url, headers=DEFAULT_HEADERS, timeout=30)
        if r.status_code == 200 and r.text:
            return r.text
        return None
    except requests.RequestException:
        return None


def playwright_verify_flow(cert: str, debug_dir: Path | None = None) -> tuple[str | None, str | None]:
    """
    Drive https://www.cgcgrading.com/verify, select each tile, enter cert,
    submit, wait for navigation, and return (final_url, html) if success.
    """
    if not PLAYWRIGHT_AVAILABLE:
        return (None, None)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=[
            "--ignore-certificate-errors",
            "--disable-blink-features=AutomationControlled",
        ])
        context = browser.new_context(
            user_agent=DEFAULT_HEADERS["User-Agent"],
            locale="en-US",
            ignore_https_errors=True,
        )
        page = context.new_page()
        try:
            page.goto(VERIFY_PORTAL, wait_until="domcontentloaded", timeout=TIMEOUT_MS)
            # Tiles are anchor/buttons; try each vertical until we reach its search form.
            for tile_text, expected_host in VERIFY_TILES:
                # Click tile (partial text match)
                tiles = page.get_by_role("link", name=lambda n: n and tile_text.lower() in n.lower())
                if not tiles or tiles.count() == 0:
                    # Try by button role too
                    tiles = page.get_by_role("button", name=lambda n: n and tile_text.lower() in n.lower())

                # If nothing matched, skip this vertical
                if not tiles or tiles.count() == 0:
                    continue

                # Click the first matching tile
                tiles.nth(0).click(timeout=TIMEOUT_MS)
                # The verify page usually opens in same tab; wait briefly
                page.wait_for_load_state("domcontentloaded", timeout=TIMEOUT_MS)

                # Look for an input for cert #
                # We try common patterns across CGC sites
                selectors = [
                    'input[placeholder*="Cert"]',
                    'input[aria-label*="Cert"]',
                    'input[name*="cert"]',
                    'input[type="text"]',
                    'input[type="search"]',
                ]
                input_box = None
                for sel in selectors:
                    matches = page.locator(sel)
                    if matches.count() > 0:
                        input_box = matches.nth(0)
                        break
                if not input_box:
                    # Go back to portal and try next tile
                    page.goto(VERIFY_PORTAL, wait_until="domcontentloaded", timeout=TIMEOUT_MS)
                    continue

                input_box.fill(cert, timeout=TIMEOUT_MS)
                # Try to submit: press Enter; also try clicking a button named "Go" or similar.
                input_box.press("Enter")
                try:
                    page.wait_for_load_state("domcontentloaded", timeout=TIMEOUT_MS)
                except PWTimeout:
                    pass

                # If still on a search page, look for a Go/Verify button
                btn = page.get_by_role("button", name=lambda n: n and any(w in n.lower() for w in ["go", "verify", "search", "look", "submit"]))
                if btn and btn.count() > 0:
                    btn.nth(0).click(timeout=TIMEOUT_MS)
                    page.wait_for_load_state("domcontentloaded", timeout=TIMEOUT_MS)

                # Wait for either a result page (URL host change or a detail layout)
                url_host = urlparse(page.url).netloc
                # Heuristic: when results load, host matches the vertical OR URL path contains 'certlookup'
                if (expected_host in url_host) or ("certlookup" in page.url.lower()) or ("cert-lookup" in page.url.lower()):
                    # If details look dynamic, give it a short render wait
                    page.wait_for_timeout(800)
                    html = page.content()
                    final_url = page.url
                    if debug_dir:
                        (debug_dir / "final_via_verify.html").write_text(html, encoding="utf-8")
                    browser.close()
                    return (final_url, html)

                # If we didn’t navigate, try next vertical
                page.goto(VERIFY_PORTAL, wait_until="domcontentloaded", timeout=TIMEOUT_MS)

        except Exception as e:
            if debug_dir:
                try:
                    (debug_dir / "error_verify.txt").write_text(repr(e), encoding="utf-8")
                    (debug_dir / "page_source_on_error.html").write_text(page.content(), encoding="utf-8")
                except Exception:
                    pass
        finally:
            browser.close()
    return (None, None)


def fetch_playwright_direct(url: str, debug_dir: Path | None = None) -> str | None:
    if not PLAYWRIGHT_AVAILABLE:
        return None
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=[
            "--ignore-certificate-errors",
            "--disable-blink-features=AutomationControlled",
        ])
        context = browser.new_context(
            user_agent=DEFAULT_HEADERS["User-Agent"],
            ignore_https_errors=True,
            locale="en-US",
        )
        page = context.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=TIMEOUT_MS)
            page.wait_for_timeout(600)
            html = page.content()
            if debug_dir:
                (debug_dir / "final_direct.html").write_text(html, encoding="utf-8")
            return html
        except Exception as e:
            if debug_dir:
                (debug_dir / "error_direct.txt").write_text(repr(e), encoding="utf-8")
            return None
        finally:
            browser.close()


def lookup_cert(cert: str, debug: bool = False) -> dict:
    result = {"cert": cert, "attempts": []}
    debug_dir = None
    if debug:
        debug_dir = Path("./cgc_debug")
        debug_dir.mkdir(exist_ok=True)

    # 1) Preferred: go through the Verify portal and let it route us.
    if PLAYWRIGHT_AVAILABLE:
        final_url, html = playwright_verify_flow(cert, debug_dir)
        attempt = {"via": "verify_portal", "status": "ok" if html else "failed", "url": final_url}
        if html:
            soup = BeautifulSoup(html, "lxml")
            data = extract_key_values(soup)
            attempt["data_found"] = bool(data)
            attempt["data"] = data
            result["attempts"].append(attempt)
            if data:
                result["best_url"] = final_url
                result["data"] = data
                return result
        else:
            attempt["data_found"] = False
            result["attempts"].append(attempt)

    # 2) Fallback: direct URL patterns (requests → Playwright)
    for pattern in DIRECT_URL_PATTERNS:
        url = pattern.format(cert=cert)
        # requests first
        html = fetch_requests(url)
        attempt = {"via": "direct_requests", "url": url, "status": "ok" if html else "blocked_or_empty"}
        if html:
            soup = BeautifulSoup(html, "lxml")
            data = extract_key_values(soup)
            attempt["data_found"] = bool(data)
            attempt["data"] = data
            result["attempts"].append(attempt)
            if data:
                result["best_url"] = url
                result["data"] = data
                return result
        else:
            result["attempts"].append(attempt)
            # try playwright direct
            html_pw = fetch_playwright_direct(url, debug_dir)
            attempt2 = {"via": "direct_playwright", "url": url, "status": "ok" if html_pw else "blocked_or_empty"}
            if html_pw:
                soup = BeautifulSoup(html_pw, "lxml")
                data = extract_key_values(soup)
                attempt2["data_found"] = bool(data)
                attempt2["data"] = data
                result["attempts"].append(attempt2)
                if data:
                    result["best_url"] = url
                    result["data"] = data
                    return result
            else:
                attempt2["data_found"] = False
                result["attempts"].append(attempt2)

    result["error"] = "Could not retrieve or parse details for this certification."
    return result


def flatten_for_csv(data: dict) -> dict:
    return {
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cert", nargs="?", help="CGC certification number")
    ap.add_argument("--out-json", dest="out_json")
    ap.add_argument("--out-csv", dest="out_csv")
    ap.add_argument("--debug", action="store_true", help="Save raw HTML to ./cgc_debug for troubleshooting")
    args = ap.parse_args()

    cert = args.cert or input("Enter CGC certification number: ").strip()
    if not cert:
        print("No cert provided."); sys.exit(1)

    result = lookup_cert(cert, debug=args.debug)
    print(json.dumps(result, indent=2, ensure_ascii=False))

    if args.out_json:
        Path(args.out_json).write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nSaved JSON → {args.out_json}")

    if args.out_csv:
        import csv
        row = flatten_for_csv(result)
        file_exists = Path(args.out_csv).exists()
        with open(args.out_csv, "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(row.keys()))
            if not file_exists:
                w.writeheader()
            w.writerow(row)
        print(f"Appended CSV row → {args.out_csv}")


if __name__ == "__main__":
    main()
