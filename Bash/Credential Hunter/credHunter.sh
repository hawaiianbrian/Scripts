#!/usr/bin/env bash
# credHunter.sh
# Description:
#   Searches for files containing credential-related terms in filenames or file contents.
#   Supports text, PDF, and Office documents (.docx, .xlsx, .pptx) if appropriate tools exist.

# Usage examples:
#   ./credHunter.sh /home /tmp/credhunt_results.csv
#   ./credHunter.sh / --check-contents /tmp/fullscan.csv

VERSION="1.0"
START_PATH="${1:-/home}"
OUTPUT_FILE="${2:-/tmp/credhunt_results.csv}"
CHECK_CONTENTS=false

# Check for optional flag
for arg in "$@"; do
  if [[ "$arg" == "--check-contents" ]]; then
    CHECK_CONTENTS=true
  fi
done

# Credential-related tokens (regex)
PATTERN="(password|pw|pwd|account|user(name)?|creds|credentials)"

# Supported extensions
SEARCH_EXTS="txt log csv env json xml yaml yml ini md pdf docx xlsx pptx rtf"

# Tools availability
HAS_PDFTOTEXT=$(command -v pdftotext >/dev/null 2>&1 && echo true || echo false)
HAS_UNZIP=$(command -v unzip >/dev/null 2>&1 && echo true || echo false)

echo "---------------------------------------------"
echo " credHunter.sh v${VERSION}"
echo " Base Path       : ${START_PATH}"
echo " Output CSV      : ${OUTPUT_FILE}"
echo " Content Scanning: ${CHECK_CONTENTS}"
echo " pdftotext found : ${HAS_PDFTOTEXT}"
echo " unzip found     : ${HAS_UNZIP}"
echo "---------------------------------------------"

echo "FullPath,FileName,Extension,MatchType,Sample,LastModified" > "${OUTPUT_FILE}"

# Find candidate files
find "$START_PATH" -type f 2>/dev/null | while read -r file; do
  ext="${file##*.}"
  ext_lower=$(echo "$ext" | tr '[:upper:]' '[:lower:]')

  # Only consider certain extensions
  if ! echo "$SEARCH_EXTS" | grep -qw "$ext_lower"; then
    continue
  fi

  fname=$(basename "$file")
  mtime=$(stat -c %y "$file" 2>/dev/null | cut -d'.' -f1)

  # Filename match
  if echo "$fname" | grep -Eiq "$PATTERN"; then
    echo "\"$file\",\"$fname\",\".$ext_lower\",\"Filename\",\"\",\"$mtime\"" >> "${OUTPUT_FILE}"
    continue
  fi

  # Optional content scanning
  if [ "$CHECK_CONTENTS" = true ]; then
    text=""
    if [[ "$ext_lower" =~ ^(txt|log|csv|env|json|xml|yaml|yml|ini|md)$ ]]; then
      text=$(grep -EIn "$PATTERN" "$file" 2>/dev/null | head -n 3)
    elif [[ "$ext_lower" == "pdf" && "$HAS_PDFTOTEXT" == "true" ]]; then
      tempout=$(mktemp)
      pdftotext -q "$file" "$tempout" 2>/dev/null
      text=$(grep -EIn "$PATTERN" "$tempout" | head -n 3)
      rm -f "$tempout"
    elif [[ "$ext_lower" =~ ^(docx|xlsx|pptx)$ && "$HAS_UNZIP" == "true" ]]; then
      tempdir=$(mktemp -d)
      unzip -qq -o "$file" -d "$tempdir" >/dev/null 2>&1
      text=$(grep -EIn "$PATTERN" "$tempdir"/*.xml 2>/dev/null | head -n 3)
      rm -rf "$tempdir"
    fi

    if [[ -n "$text" ]]; then
      sample=$(echo "$text" | tr '\n' ' ' | sed 's/"/'\''/g')
      echo "\"$file\",\"$fname\",\".$ext_lower\",\"Content\",\"$sample\",\"$mtime\"" >> "${OUTPUT_FILE}"
    fi
  fi
done

echo "---------------------------------------------"
echo " Scan complete."
echo " Results saved to: ${OUTPUT_FILE}"
echo "---------------------------------------------"
