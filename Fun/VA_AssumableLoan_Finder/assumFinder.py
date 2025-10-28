#!/usr/bin/env python3
"""
Zillow ASSUM Loan Finder
------------------------
Prompts the user for a ZIP code and opens Zillow search results
showing listings that contain 'ASSUM' in their description.
"""

import urllib.parse
import webbrowser

def make_zillow_url(zipcode: str) -> str:
    """Build the Zillow search URL for listings containing 'ASSUM'."""
    zipcode = zipcode.strip()
    if not zipcode.isdigit():
        raise ValueError("Please enter a valid 5-digit ZIP code.")
    return f"https://www.zillow.com/homes/{zipcode}_rb/?keywordText=ASSUM"

def main():
    print("=== Zillow ASSUM Loan Finder ===")
    zipcode = input("Enter ZIP code (e.g., 31401): ").strip()
    try:
        url = make_zillow_url(zipcode)
        print(f"\n🔎 Searching Zillow for listings with 'ASSUM' in {zipcode}...\n{url}\n")
        webbrowser.open_new_tab(url)
    except ValueError as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
