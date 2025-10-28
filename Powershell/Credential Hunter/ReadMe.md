# 🔐 credHunter.ps1 — Credential Discovery Utility

![PowerShell](https://img.shields.io/badge/PowerShell-5.1%2B-blue)
![Windows](https://img.shields.io/badge/Platform-Windows-lightgrey)
![Status](https://img.shields.io/badge/Status-Production-green)

`credHunter.ps1` is a PowerShell utility for **detecting plaintext credentials** left on Windows endpoints.  
It identifies files whose **filenames or contents** may expose sensitive data such as passwords or account information.

Designed for **SOC analysts, threat hunters, and IR responders**, this tool helps enforce credential hygiene and prevent accidental data leaks.

---

## 🧩 Features

| Capability | Description |
|-------------|--------------|
| 🔍 **Filename scanning** | Finds files whose names contain words like `password`, `creds`, `account`, `username`, etc. |
| 🧠 **Content scanning (optional)** | Scans inside text-based files for the same tokens. |
| 📄 **PDF parsing** | If `pdftotext.exe` (Poppler) is present, extracts and searches PDF text. |
| 🧾 **Office document parsing** | Reads `.docx`, `.xlsx`, `.pptx` contents via built-in .NET Zip methods. |
| ⚙️ **Graceful fallback** | Skips unsupported files or missing tools silently. |
| 📊 **CSV reporting** | Exports a structured CSV report with file path, type, timestamp, and sample match. |

---

## ⚙️ Supported File Types

| Category | Extensions | Content Scanned? |
|-----------|-------------|------------------|
| **Text / Config / Logs** | `.txt`, `.log`, `.csv`, `.env`, `.json`, `.xml`, `.yaml`, `.ini`, `.md` | ✅ Yes |
| **PDF Documents** | `.pdf` | ✅ If `pdftotext.exe` present |
| **Office (OpenXML)** | `.docx`, `.xlsx`, `.pptx` | ✅ Native XML extraction |
| **Legacy Office / RTF** | `.doc`, `.xls`, `.ppt`, `.rtf` | ❌ Filename only |
| **Scripts** | `.ps1`, `.bat`, `.cmd`, `.sh` | ✅ Yes (if text-based) |

---

## 🚀 Usage

### 1. Filename-Only Scan (Fast)
```powershell
.\credHunter.ps1 -Path "C:\Users" -OutputCsv "C:\Temp\credhunt_results.csv"
