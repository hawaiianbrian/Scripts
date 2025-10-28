#!/usr/bin/env python3
"""
Zillow ASSUM Finder (ZIP-wide)
- Prompts for a ZIP code
- Opens Zillow's results for that ZIP
- Enters 'ASSUM' into the Keyword filter (like you do manually)
- Scrolls to load all results
- Exports every matching listing (URL, address, price, beds, baths, sqft) to CSV
"""

import csv
import json
import re
import time
from pathlib import Path
from typing import List, Dict, Any

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

def build_zip_url(zipcode: str) -> str:
    zipcode = zipcode.strip()
    # canonical ZIP results path; we'll set the keyword via the UI
    return f"https://www.zillow.com/homes/{zipcode}_rb/"

def human_sleep(sec: float):
    # small helper to avoid hammering the page
    time.sleep(sec)

def safe_text(el):
    try:
        return (el.inner_text() or "").strip()
    except Exception:
        return ""

def parse_number(txt: str) -> str:
    txt = (txt or "").strip()
    return re.sub(r"[^\d.]", "", txt)

def scroll_to_load_all(page, max_rounds: int = 40, pause: float = 0.8) -> None:
    """Scrolls the results pane (or window) to load more listings."""
    # Try to find the scrollable list pane (left column) if present
    scrollers = [
        "[data-testid='search-page-list-container']",
        "ul.photo-cards",
        "div#grid-search-results",
        "div.search-page-list-container",
    ]
    last_count = -1
    same_count_rounds = 0

    for i in range(max_rounds):
        # Count current result cards
        count = len(page.query_selector_all("article, li.ListItem-c11n-8-100-0__sc-1sm0yul-0, li[data-test='property-card'], div.property-card"))
        if count == last_count:
            same_count_rounds += 1
        else:
            same_count_rounds = 0
        last_count = count

        # Stop if we haven't loaded anything new for a few rounds
        if same_count_rounds >= 3:
            break

        # Try scrolling the results pane; fall back to window scroll
        scrolled = False
        for sel in scrollers:
            pane = page.query_selector(sel)
            if pane:
                page.eval_on_selector(sel, "el => el.scrollTo(0, el.scrollHeight)")
                scrolled = True
                break
        if not scrolled:
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

        human_sleep(pause)

def set_keyword_filter(page, keyword: str = "ASSUM"):
    """
    Sets the Zillow 'Keyword' filter using the on-page control.
    Falls back to directly mutating searchQueryState if the control isn't found.
    """
    # Common selectors for the keyword box
    candidates = [
        "input[name='keywordText']",
        "[data-testid='search-bar-keyword-input'] input",
        "[data-testid='search-page-keyword-box'] input",
        "input#keyword",
        "input[placeholder*='Keyword']",
    ]

    # 1) Try the visible keyword input path (preferred)
    for sel in candidates:
        try:
            kw = page.wait_for_selector(sel, timeout=2500)
            kw.click()
            kw.fill("")  # clear
            kw.type(keyword)
            kw.press("Enter")
            # wait a moment for results to refresh
            human_sleep(2.0)
            return
        except PWTimeout:
            continue
        except Exception:
            continue

    # 2) Fallback: mutate searchQueryState and reload (works like your URL example)
    try:
        # Grab current URL and searchQueryState
        url = page.evaluate("() => location.href")
        from urllib.parse import urlparse, parse_qs, urlencode, urlunparse, quote, unquote

        parts = urlparse(url)
        qs = parse_qs(parts.query)
        sqs_raw = qs.get("searchQueryState", [None])[0]
        if sqs_raw:
            try:
                sqs = json.loads(unquote(sqs_raw))
            except Exception:
                sqs = {}
        else:
            # create a minimal searchQueryState
            sqs = {
                "pagination": {},
                "isMapVisible": True,
                "isListVisible": True,
                "mapZoom": 12,
            }

        # Zillow sometimes uses 'keywords' key; sometimes 'att' for the keyword text
        filter_state = sqs.get("filterState", {})
        # prefer 'keywords' (typical) but set both for safety
        filter_state["keywords"] = {"value": keyword}
        filter_state["att"] = {"value": keyword}
        sqs["filterState"] = filter_state

        # also set usersSearchTerm to the current location path (helps Zillow resolve region)
        path_bits = [p for p in parts.path.split("/") if p]
        if path_bits:
            sqs["usersSearchTerm"] = path_bits[-1].replace("_rb", "")

        # rebuild URL
        qs["searchQueryState"] = [quote(json.dumps(sqs, separators=(",", ":")))]
        new_query = urlencode(qs, doseq=True)
        new_url = urlunparse((parts.scheme, parts.netloc, parts.path, parts.params, new_query, parts.fragment))

        page.goto(new_url, wait_until="domcontentloaded")
        human_sleep(2.0)
    except Exception:
        pass

def extract_cards(page) -> List[Dict[str, Any]]:
    """
    Extracts listing info from visible result cards.
    We check multiple selector patterns to be resilient.
    """
    records: List[Dict[str, Any]] = []
    card_selectors = [
        "article",
        "li.ListItem-c11n-8-100-0__sc-1sm0yul-0",
        "li[data-test='property-card']",
        "div.property-card",
    ]

    for sel in card_selectors:
        for card in page.query_selector_all(sel):
            txt = safe_text(card).lower()
            if "assum" not in txt:
                # The list is already filtered by keyword, but we keep a safety check.
                continue

            # Try to grab structured fields
            url = ""
            a = card.query_selector("a")
            if a:
                try:
                    url = a.get_attribute("href") or ""
                    if url.startswith("/"):
                        url = "https://www.zillow.com" + url
                except Exception:
                    pass

            address = ""
            for adr_sel in [
                "[data-test='property-card-addr']",
                "[data-test='property-card-price'] ~ div",  # sometimes address is near price
                "address",
                "h3",
                "span",
            ]:
                el = card.query_selector(adr_sel)
                address = safe_text(el)
                if address:
                    break

            price = ""
            for pr_sel in [
                "[data-test='property-card-price']",
                "span[data-testid='price']",
                "span:has-text('$')",
            ]:
                el = card.query_selector(pr_sel)
                price = safe_text(el)
                if price:
                    break

            # Beds / baths / sqft often appear as small chips
            beds = baths = sqft = ""
            chips = card.query_selector_all("[data-test='property-card-beds'], [data-test='property-card-baths'], [data-test='property-card-sqft'], li, span")
            for chip in chips:
                t = safe_text(chip)
                tl = t.lower()
                if not beds and ("bd" in tl or "bed" in tl) and re.search(r"\d", t):
                    beds = t
                elif not baths and ("ba" in tl or "bath" in tl) and re.search(r"\d", t):
                    baths = t
                elif not sqft and ("sqft" in tl or "sq ft" in tl):
                    sqft = t

            records.append({
                "address": address,
                "price": price,
                "beds": beds,
                "baths": baths,
                "sqft": sqft,
                "url": url,
            })

    # Deduplicate by URL
    seen = set()
    unique = []
    for rec in records:
        key = rec.get("url") or rec.get("address")
        if key and key not in seen:
            unique.append(rec)
            seen.add(key)
    return unique

def main():
    zipcode = input("Enter ZIP code (e.g., 80134): ").strip()
    if not zipcode.isdigit() or len(zipcode) not in (5, 9):
        print("Please enter a numeric ZIP (5 or 9 digits).")
        return

    url = build_zip_url(zipcode)
    out_csv = OUTPUT_DIR / f"assum_listings_{zipcode}.csv"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()  # consider setting a desktop UA if needed
        page = context.new_page()

        print(f"Opening {url}")
        page.goto(url, wait_until="domcontentloaded")
        # Give time for client JS to initialize
        human_sleep(2.0)

        # Set 'ASSUM' in keyword filter (UI or fallback)
        print("Applying keyword filter: ASSUM")
        set_keyword_filter(page, "ASSUM")

        # Wait for list to refresh (look for a results container)
        try:
            page.wait_for_selector("[data-testid='search-page-list-container'], ul.photo-cards, div#grid-search-results", timeout=8000)
        except PWTimeout:
            pass

        # Load everything by scrolling
        print("Scrolling to load all results…")
        scroll_to_load_all(page)

        # Extract records
        print("Extracting listings…")
        records = extract_cards(page)

        # Save CSV
        with out_csv.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["address", "price", "beds", "baths", "sqft", "url"])
            writer.writeheader()
            writer.writerows(records)

        browser.close()

    print(f"Done. Found {len(records)} listings with 'ASSUM' in {zipcode}.")
    print(f"Saved: {out_csv.resolve()}")

if __name__ == "__main__":
    main()
