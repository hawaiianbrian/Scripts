# 🕵️‍♂️ CGC Certification Lookup Tool

A Python utility that retrieves and parses **Certified Guaranty Company (CGC)** certification data directly from the official verification site.

This script automates the lookup of **CGC Comics, Cards, Video Games, and Home Video** certification numbers by simulating a browser session through the official [CGC Verify portal](https://www.cgcgrading.com/verify).  
If needed, it falls back to direct lookup URLs and gracefully handles bot protection (Cloudflare/WAF) using a headless Chromium browser via **Playwright**.

---

## 🚀 Features

- ✅ **Automatic category detection** — Tries Comics, Cards, Video Games, and Home Video.
- 🔄 **Headless browser automation** using Playwright to bypass WAF.
- 🧠 **Smart parsing** of CGC pages to extract:
  - Title, grade, and series information  
  - JSON-LD structured data  
  - Meta tags (OpenGraph/Twitter)
  - Definition list and table fields (details, grade info, etc.)
  - Associated images (cover/front/back)
- 💾 **Optional output files:**
  - JSON for structured data
  - CSV for quick spreadsheet tracking
- 🪄 **Debug mode** to save raw HTML for troubleshooting.

---

## 📦 Requirements

Python **3.9+**

Install dependencies:

```bash
pip install requests beautifulsoup4 lxml python-slugify playwright
python -m playwright install chromium
