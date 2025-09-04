# daddylive_iptv.py
import requests
from bs4 import BeautifulSoup
from flask import Flask, send_file, render_template_string
import threading
import time
import os

app = Flask(__name__)
M3U_FILE = "daddylive.m3u"

# --- Scraping functions ---

def scrape_daddylive():
    """Scrape DaddyLive for streams (USA)"""
    channels = []
    try:
        r = requests.get("https://daddylive.sx/", timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.select("a.stream-link"):  # adjust selector
            name = a.text.strip()
            url = a.get("href")
            if url and name:
                channels.append({
                    "name": name,
                    "url": url,
                    "group": "USA (DaddyLive)",
                    "logo": ""
                })
    except Exception as e:
        print(f"Failed to scrape DaddyLive: {e}")
    return channels

def scrape_uk_source():
    """Scrape UK TV source with categories"""
    channels = []
    category_map = {
        "Sports": "UK Sports",
        "News": "UK News",
        "Entertainment": "UK Entertainment"
    }
    try:
        r = requests.get("https://uk-example-tv-site.com/", timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        for div in soup.select("div.channel-card"):  # adjust selector
            name = div.select_one("h4.name").text.strip()
            url = div.select_one("a.play")["href"]
            category_raw = div.get("data-category", "Other")
            group = category_map.get(category_raw, "UK Other")
            logo = div.select_one("img")["src"] if div.select_one("img") else ""
            channels.append({
                "name": name,
                "url": url,
                "group": group,
                "logo": logo
            })
    except Exception as e:
        print(f"Failed to scrape UK source: {e}")
    return channels

# --- M3U generation ---
def generate_m3u(channels):
    with open(M3U_FILE, "w", encoding="utf-8") as f:
        f.write(f"#EXTM3U url-tvg=\"https://raw.githubusercontent.com/yourusername/automatic-chainsaw/main/epg.xml\"\n")
        for ch in channels:
            f.write(
                f'#EXTINF:-1 tvg-id="{ch["name"]}" tvg-name="{ch["name"]}" tvg-logo="{ch["logo"]}" '
                f'group-title="{ch["group"]}",{ch["name"]}\n'
            )
            f.write(f'{ch["url"]}\n')
    print(f"✅ Generated M3U with {len(channels)} channels")

# --- Auto-refresh ---
def refresh_loop(interval=3600):
    while True:
        all_channels = []
        all_channels.extend(scrape_daddylive())
        all_channels.extend(scrape_uk_source())
        generate_m3u(all_channels)
        time.sleep(interval)

threading.Thread(target=refresh_loop, daemon=True).start()

# --- Flask routes ---
@app.route("/")
def index():
    return render_template_string("""
        <h2>✅ DaddyLive IPTV server is running!</h2>
        <ul>
            <li>Playlist: <a href="/daddylive.m3u">/daddylive.m3u</a></li>
        </ul>
    """)

@app.route("/daddylive.m3u")
def playlist():
    return send_file(M3U_FILE)

if __name__ == "__main__":
    if not os.path.exists(M3U_FILE):
        generate_m3u([])  # create empty file initially
    app.run(host="0.0.0.0", port=8080)
