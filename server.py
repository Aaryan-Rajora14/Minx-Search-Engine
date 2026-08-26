#!/usr/bin/env python3
"""MINX — stdlib-only server. No pip packages required."""
from __future__ import annotations

import json
import os
import re
import urllib.parse
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
STORIES = json.loads((ROOT / "stories.json").read_text(encoding="utf-8"))
HOST = os.environ.get("MINX_HOST", "0.0.0.0")
PORT = int(os.environ.get("MINX_PORT", "8080"))
BLOCKED = re.compile(
    r"\b(nsfw|porn|xxx|onlyfans|nude|nudes|sex tape|explicit|child|minor|suicide|self[- ]harm)\b",
    re.I,
)

TOPICS = [
    "friends", "family", "study", "gossip", "work",
    "neighbors", "fantasy", "politics", "secrets",
]

HOOKS = [
    "the group chat leak", "the seating chart", "the shared notes folder",
    "the intern roast", "the balcony plants", "the wrong voice note",
    "the solo trip overlap", "the last-minute slides", "the remixed story",
    "the cake nickname", "the lockscreen photo", "the library snack market",
    "the too-specific gift", "the laminated neighbor note", "the candid photographer",
    "the wifi password rumor", "the labeled fridge", "the mysterious A+",
    "the snack-budget all-hands", "the aunt who knows everything",
]
CASTS = [
    "college friends", "cousins", "roommates", "office pod", "book club",
    "study group", "campaign volunteers", "larp table", "downstairs neighbors",
    "family WhatsApp", "secret Santa circle", "HOA committee",
]


def google_url(q: str) -> str:
    return "https://www.google.com/search?q=" + urllib.parse.quote_plus(q) + "&num=100"


def catalog(topic: str, mode: str, query: str) -> list[dict]:
    topics = TOPICS if topic == "all" else [topic]
    heat = "unhinged" if mode == "unhinged" else "family"
    q = query.strip().lower()
    out: list[dict] = []
    n = 0
    for t in topics:
        for hook in HOOKS:
            for cast in CASTS:
                n += 1
                title = f"{cast.title()} and {hook} — {t} tea"
                snippet = (
                    f"A {t} story about {cast} and {hook}. "
                    "Open the Google result to read public posts, forums, and recaps."
                )
                hay = f"{title} {snippet} {t} {query}".lower()
                if q and q not in hay and not all(tok in hay for tok in q.split() if len(tok) > 1):
                    if n % 3 != 0:
                        continue
                out.append(
                    {
                        "id": f"g-{t}-{n}",
                        "title": title,
                        "snippet": snippet,
                        "source": "Google",
                        "url": google_url(f"{t} {hook} {cast} story gossip"),
                        "topic": t,
                        "tags": [t, hook, "google"],
                        "heat": heat,
                    }
                )
    return out


def match_archive(query: str, topic: str, mode: str) -> list[dict]:
    q = query.strip().lower()
    tokens = [t for t in q.split() if len(t) > 1]
    out = []
    for s in STORIES:
        if mode == "family" and s.get("heat") != "family":
            continue
        if topic != "all" and s.get("topic") != topic:
            continue
        hay = f"{s['title']} {s['snippet']} {' '.join(s.get('tags', []))} {s.get('topic','')}".lower()
        if q and not (q in hay or all(t in hay for t in tokens)):
            continue
        out.append(s)
    return out


def search_reddit(query: str, topic: str, mode: str) -> list[dict]:
    q = query.strip() or (topic if topic != "all" else "story gossip")
    extra = (
        "(story OR AITA OR secret OR drama OR gossip)"
        if mode == "unhinged"
        else "(story OR roommate OR family OR college OR gossip)"
    )
    url = "https://www.reddit.com/search.json?" + urllib.parse.urlencode(
        {"q": f"{q} {extra}", "sort": "relevance", "t": "year", "limit": "25", "type": "link"}
    )
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "MINX-tea-search/1.0", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=6) as resp:
            body = json.loads(resp.read().decode("utf-8", "replace"))
    except Exception:
        return []
    out = []
    for child in body.get("data", {}).get("children", []):
        d = child.get("data") or {}
        title = (d.get("title") or "").strip()
        if not title or d.get("over_18") or d.get("stickied"):
            continue
        text = f"{title} {d.get('selftext') or ''}"
        if BLOCKED.search(text):
            continue
        permalink = d.get("permalink")
        link = f"https://www.reddit.com{permalink}" if permalink else d.get("url")
        if not link:
            continue
        out.append(
            {
                "id": f"r-{link}",
                "title": re.sub(r"\s+", " ", title),
                "snippet": re.sub(
                    r"\s+", " ", d.get("selftext") or f"From r/{d.get('subreddit','reddit')}"
                ).strip()[:280],
                "source": "Reddit",
                "url": link,
                "topic": topic if topic != "all" else "gossip",
                "tags": [d.get("subreddit") or "reddit", "live"],
                "heat": mode,
            }
        )
    return out


def do_search(query: str, topic: str, mode: str) -> dict:
    topic = topic if topic in TOPICS or topic == "all" else "all"
    mode = "unhinged" if mode == "unhinged" else "family"
    archive = match_archive(query, topic, mode)
    live: list[dict] = []
    try:
        live = search_reddit(query, topic, mode)
    except Exception:
        live = []
    web = catalog(topic, mode, query)
    seen = set()
    stories = []
    for s in live + archive + web:
        key = s["title"].lower()
        if key in seen:
            continue
        seen.add(key)
        stories.append(s)
        if len(stories) >= 120:
            break
    qmix = " ".join(x for x in [query, topic if topic != "all" else "", "story"] if x)
    return {
        "stories": stories,
        "liveCount": len(live),
        "archiveCount": len(archive),
        "googleUrl": google_url(qmix or "tea stories"),
        "redditUrl": "https://www.reddit.com/search/?q=" + urllib.parse.quote_plus(qmix or "story"),
        "quoraUrl": "https://www.quora.com/search?q=" + urllib.parse.quote_plus(qmix or "story"),
        "mode": mode,
    }


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC), **kwargs)

    def log_message(self, fmt, *args):
        return

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path in ("/", "/index.html"):
            return self._send_file(STATIC / "index.html", "text/html; charset=utf-8")
        if parsed.path == "/api/search":
            qs = urllib.parse.parse_qs(parsed.query)
            payload = do_search(
                (qs.get("q") or [""])[0][:160],
                (qs.get("topic") or ["all"])[0],
                (qs.get("mode") or ["family"])[0],
            )
            data = json.dumps(payload).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        return super().do_GET()

    def _send_file(self, path: Path, ctype: str):
        raw = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def main():
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"MINX running on http://{HOST}:{PORT}", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
