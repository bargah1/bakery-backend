import urllib.request
import zipfile
import os

download_url = "https://github.com/supabase/cli/releases/latest/download/supabase_windows_amd64.zip"
print(f"Downloading from {download_url}...")
req = urllib.request.Request(download_url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req) as response:
    with open("supabase.zip", "wb") as f:
        f.write(response.read())

print("Extracting...")
with zipfile.ZipFile("supabase.zip", 'r') as zip_ref:
    zip_ref.extractall(".")
print("Done! supabase.exe is ready.")
