# 🔐 credHunter.sh — Credential Discovery Utility (Linux/macOS)

![Bash](https://img.shields.io/badge/Bash-4.0%2B-blue)
![Linux](https://img.shields.io/badge/Platform-Linux%2FmacOS-lightgrey)
![Status](https://img.shields.io/badge/Status-Production-green)

`credHunter.sh` is a lightweight Bash script that detects **plaintext credentials** on Linux or macOS systems.  
It scans for suspicious filenames and optionally inspects file contents for words like `password`, `creds`, or `account`.

Built for **SOC analysts, sysadmins, and IR responders**, it helps identify potential credential leaks during threat hunts or compliance audits.

---

## 🧩 Features

| Capability | Description |
|-------------|--------------|
| 🔍 **Filename scanning** | Finds files whose names contain keywords like `password`, `pw`, `creds`, `account`, etc. |
| 🧠 **Content scanning (optional)** | Reads file contents for the same patterns (text, PDF, Office). |
| 📄 **PDF parsing** | Uses `pdftotext` if installed. |
| 🧾 **Office parsing** | Uses `unzip` to extract and scan `.docx`, `.xlsx`, `.pptx` XML data. |
| ⚙️ **Graceful fallback** | Skips unsupported formats/tools safely. |
| 📊 **CSV output** | Exports all findings to a simple, parseable CSV file. |

---

## ⚙️ Supported File Types

| Category | Extensions | Content Scanned? |
|-----------|-------------|------------------|
| **Text / Config / Logs** | `.txt`, `.log`, `.csv`, `.env`, `.json`, `.xml`, `.yaml`, `.yml`, `.ini`, `.md` | ✅ Yes |
| **PDF Documents** | `.pdf` | ✅ If `pdftotext` installed |
| **Office (OpenXML)** | `.docx`, `.xlsx`, `.pptx` | ✅ If `unzip` installed |
| **Legacy / RTF** | `.doc`, `.xls`, `.ppt`, `.rtf` | ❌ Filename only |

---

## 🚀 Usage

### 1. Filename-Only Scan (Fast)
```bash
sudo ./credHunter.sh /home /tmp/credhunt_results.csv
