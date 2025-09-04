import os
import re
import time
import threading
import requests
from flask import Flask, Response, render_template_string, request

app = Flask(__name__)

# =========================
# CONFIG
# =========================
REFRESH_INTERVAL = 1800  # 30 minutes
channels = []

# Static sources
SOURCES = {
    "DaddyLive": "https://raw.githubusercontent.com/dtankdempse/daddylive-m3u/refs/heads/main/daddylive.m3u",
    "LiveHDTV": "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/us.m3u",
    "UKFree": "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/gb.m3u",
    "LiveTVsx": "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/sport.m3u",
}

FALLBACK_REPO = "https://raw.githubusercontent.com/iptv-org/iptv/master/index.m3u"

CATEGORY_MAP = {
    "UK": ["UK", "BBC", "ITV", "Sky", "BT Sport", "Premier League", "Channel 4", "Channel 5"],
    "Sports": ["Sport", "ESPN", "Sky Sports", "BT Sport", "Fox Sports", "beIN"],
    "USA": ["USA", "NBC", "CBS", "ABC", "FOX", "CW", "PBS"],
    "News": ["News", "CNN", "BBC News", "Sky News", "Fox News", "MSNBC", "Bloomberg", "Al Jazeera"],
    "Movies": ["HBO", "Cinemax", "Showtime", "Starz", "Movie", "Film"],
    "Kids": ["Cartoon", "Disney", "Nick", "Boomerang", "Pogo"],
    "General": ["Channel", "TV"],
}

# =========================
# HELPER FUNCTIONS
# =========================
def fetch_m3u(url):
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        print(f"❌ Failed to fetch {url}: {e}")
        return ""


def discover_fallbacks():
    fallback_urls = []
    try:
        print("🔎 Discovering fallback sources...")
        m3u_index = fetch_m3u(FALLBACK_REPO)
        for line in m3u_index.splitlines():
            if line.startswith("http") and line.endswith(".m3u"):
                fallback_urls.append(line.strip())
        print(f"✅ Found {len(fallback_urls)} fallback playlists.")
    except Exception as e:
        print(f"⚠️ Fallback discovery failed: {e}")
    return fallback_urls[:5]


def categorize_channel(name):
    for cat, keywords in CATEGORY_MAP.items():
        for keyword in keywords:
            if keyword.lower() in name.lower():
                return cat
    return "Other"


def parse_m3u(source_name, m3u_content, proxy=False):
    lines = m3u_content.splitlines()
    parsed = []
    for i in range(len(lines)):
        if lines[i].startswith("#EXTINF"):
            meta = lines[i]
            url = lines[i + 1] if i + 1 < len(lines) else None
            if not url or not url.startswith("http"):
                continue

            tvg_name = re.search(r'tvg-name="(.*?)"', meta)
            tvg_logo = re.search(r'tvg-logo="(.*?)"', meta)
            group_title = re.search(r'group-title="(.*?)"', meta)

            name = tvg_name.group(1) if tvg_name else meta.split(",")[-1]
            logo = tvg_logo.group(1) if tvg_logo else ""
            group = group_title.group(1) if group_title else ""

            category = categorize_channel(name)

            # If proxy=True, we route through /proxy/<id>
            parsed.append({
                "name": f"{source_name} - {name}",
                "url": url if not proxy else None,
                "proxy": proxy,
                "original_url": url,
                "logo": logo,
                "group": f"{source_name} - {category}",
            })
    return parsed


def refresh_channels():
    global channels
    new_channels = []
    channel_id = 1

    for source, url in SOURCES.items():
        print(f"🔄 Fetching from {source}...")
        m3u_content = fetch_m3u(url)
        if m3u_content:
            # Only DaddyLive requires proxy
            proxy_required = True if source == "DaddyLive" else False
            parsed = parse_m3u(source, m3u_content, proxy=proxy_required)
            for ch in parsed:
                ch['id'] = channel_id
                channel_id += 1
            new_channels.extend(parsed)
            print(f"✅ {source}: Loaded {len(parsed)} channels.")
        else:
            print(f"⚠️ {source}: No channels loaded.")

    for fb_url in discover_fallbacks():
        fb_content = fetch_m3u(fb_url)
        if fb_content:
            parsed = parse_m3u("GitHubFree", fb_content, proxy=True)
            for ch in parsed:
                ch['id'] = channel_id
                channel_id += 1
            new_channels.extend(parsed)

    channels = new_channels
    print(f"📺 Total channels loaded: {len(channels)}")


def auto_refresh():
    while True:
        refresh_channels()
        time.sleep(REFRESH_INTERVAL)


# =========================
# FLASK ROUTES
# =========================
@app.route("/")
def home():
    return """
    <h2>DaddyLive IPTV server is running!</h2>
    <p><a href='/daddylive.m3u'>Playlist (M3U)</a></p>
    <p><a href='/ui'>Web UI</a></p>
    """


@app.route("/daddylive.m3u")
def playlist():
    def generate():
        yield "#EXTM3U\n"
        for ch in channels:
            if ch["proxy"]:
                yield f'#EXTINF:-1 tvg-logo="{ch["logo"]}" group-title="{ch["group"]}",{ch["name"]}\n/proxy/{ch["id"]}\n'
            else:
                yield f'#EXTINF:-1 tvg-logo="{ch["logo"]}" group-title="{ch["group"]}",{ch["name"]}\n{ch["original_url"]}\n'
    return Response(generate(), mimetype="audio/x-mpegurl")


@app.route("/proxy/<int:channel_id>")
def proxy_stream(channel_id):
    ch = next((c for c in channels if c['id'] == channel_id), None)
    if not ch:
        return "Channel not found", 404

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": ch["original_url"]
    }

    def generate():
        with requests.get(ch["original_url"], headers=headers, stream=True) as r:
            for chunk in r.iter_content(chunk_size=1024*16):
                if chunk:
                    yield chunk

    return Response(generate(), content_type='application/vnd.apple.mpegurl')


@app.route("/ui")
def ui():
    html = """
    <html><head><title>DaddyLive IPTV</title></head>
    <body style="font-family:Arial;">
    <h2>📺 DaddyLive IPTV Web UI</h2>
    <ul>
    {% for ch in channels %}
      <li>
        <img src="{{ ch.logo }}" width="30" style="vertical-align:middle;">
        <b>{{ ch.name }}</b> ({{ ch.group }})
        <a href="{{ '/proxy/' + str(ch.id) if ch.proxy else ch.original_url }}" target="_blank">▶ Play</a>
      </li>
    {% endfor %}
    </ul>
    </body></html>
    """
    return render_template_string(html, channels=channels)


# =========================
# MAIN ENTRY
# =========================
if __name__ == "__main__":
    threading.Thread(target=auto_refresh, daemon=True).start()
    refresh_channels()
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
