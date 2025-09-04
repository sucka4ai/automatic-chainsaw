import os
import time
import threading
import requests
from flask import Flask, Response, jsonify

app = Flask(__name__)

M3U_URL = "https://daddylive.sx"
PLAYLIST_FILE = "daddylive.m3u"
EPG_FILE = "epg.xml"

channels = []
last_refresh = 0

def fetch_channels():
    global channels, last_refresh
    try:
        # Simulated: You would scrape or fetch channels here
        channels = [
            {
                "id": 1,
                "name": "BBC One",
                "url": "https://xyzdddd.videohls.ru/lb/premium51/index.m3u8",
                "logo": "https://upload.wikimedia.org/wikipedia/en/1/1a/BBC_One_logo_2021.svg",
                "group": "UK"
            },
            {
                "id": 2,
                "name": "Sky Sports",
                "url": "https://xyzdddd.videohls.ru/lb/premium302/index.m3u8",
                "logo": "https://upload.wikimedia.org/wikipedia/en/c/cf/Sky_Sports_logo_2020.svg",
                "group": "Sports"
            }
        ]
        last_refresh = time.time()
        print(f"✅ Loaded {len(channels)} channels.")
    except Exception as e:
        print(f"❌ Failed to fetch channels: {e}")

def auto_refresh(interval=300):
    while True:
        fetch_channels()
        time.sleep(interval)

@app.route("/")
def index():
    return "✅ DaddyLive IPTV server is running!<br>Playlist: /daddylive.m3u<br>EPG: /epg.xml<br>UI: /ui"

@app.route("/daddylive.m3u")
def playlist():
    m3u = "#EXTM3U\n"
    for ch in channels:
        m3u += f'#EXTINF:-1 tvg-id="{ch["id"]}" tvg-name="{ch["name"]}" tvg-logo="{ch["logo"]}" group-title="{ch["group"]}",{ch["name"]}\n'
        m3u += f'{ch["url"]}\n'
    return Response(m3u, mimetype="audio/x-mpegurl")

@app.route("/epg.xml")
def epg():
    xml = "<?xml version=\"1.0\" encoding=\"UTF-8\" ?><tv></tv>"
    return Response(xml, mimetype="application/xml")

@app.route("/ui")
def ui():
    html = "<h1>DaddyLive IPTV</h1><ul>"
    for ch in channels:
        html += f'<li><img src="{ch["logo"]}" width="30"> {ch["name"]} - <a href="{ch["url"]}">Play</a></li>'
    html += "</ul>"
    return html

if __name__ == "__main__":
    threading.Thread(target=auto_refresh, daemon=True).start()
    fetch_channels()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
