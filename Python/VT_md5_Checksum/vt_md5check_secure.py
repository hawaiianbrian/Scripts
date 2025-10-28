import hashlib
import os
import requests
import sys
from dotenv import load_dotenv

# Load environment variables from .env (optional)
load_dotenv()

VT_URL = "https://www.virustotal.com/api/v3/files/"

def get_md5(file_path):
    """Calculate MD5 checksum of a file."""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def check_virustotal(md5_hash, api_key):
    """Check the MD5 hash on VirusTotal."""
    headers = {"x-apikey": api_key}
    response = requests.get(VT_URL + md5_hash, headers=headers)

    if response.status_code == 200:
        data = response.json()
        stats = data.get("data", {}).get("attributes", {}).get("last_analysis_stats", {})
        print(f"\nVirusTotal Results for {md5_hash}:")
        print(f"  Malicious: {stats.get('malicious', 0)}")
        print(f"  Suspicious: {stats.get('suspicious', 0)}")
        print(f"  Undetected: {stats.get('undetected', 0)}")
    elif response.status_code == 404:
        print(f"\nHash {md5_hash} not found on VirusTotal.")
    else:
        print(f"\nError: {response.status_code} - {response.text}")

def main():
    if len(sys.argv) != 2:
        print("Usage: python vt_md5check_secure.py <file_path>")
        sys.exit(1)

    api_key = os.getenv("VT_API_KEY")
    if not api_key:
        print("Error: Please set your VirusTotal API key as an environment variable:")
        print("  export VT_API_KEY='your_api_key_here'  (Linux/macOS)")
        print("  setx VT_API_KEY 'your_api_key_here'    (Windows)")
        sys.exit(1)

    file_path = sys.argv[1]
    md5_hash = get_md5(file_path)
    print(f"MD5: {md5_hash}")
    check_virustotal(md5_hash, api_key)

if __name__ == "__main__":
    main()
