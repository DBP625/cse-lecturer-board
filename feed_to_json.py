#!/usr/bin/env python3
"""
feed_to_json.py -- turn Google Alerts RSS/Atom feed(s) into notices.json
for the CSE Lecturer notice board.

No third-party dependencies (Python standard library only), so it runs on a
bare GitHub Actions runner with nothing to install.

Feed URLs are read from the FEED_URLS environment variable (comma- OR
newline-separated). As a fallback it reads a local feeds.txt file
(one URL per line; blank lines and lines starting with # are ignored).

Get a feed URL: create a Google Alert, set "Deliver to" = RSS feed, then
copy the feed link from the RSS icon on your alerts page.
"""

import os
import re
import sys
import json
import html
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from xml.etree import ElementTree as ET

ATOM = "{http://www.w3.org/2005/Atom}"

# Keep an entry only if it looks like an actual job posting, not news that
# merely mentions a CSE department. Rule: a hiring ROLE word on its own is
# enough (e.g. "Lecturer"), OR a FIELD mention together with a JOB_INTENT word.
# This drops event/news articles that name "Computer Science" but no vacancy.
# Note: bare "professor" is deliberately NOT a role word here -- news articles
# quote professors constantly.
ROLE = re.compile(r"lecturer|faculty|assistant professor|senior lecturer|প্রভাষক", re.I)
JOB_INTENT = re.compile(
    r"recruit|vacan|circular|apply|hiring|appointment|position|career|"
    r"walk-?in|wanted|opening|নিয়োগ|বিজ্ঞপ্তি", re.I)
FIELD = re.compile(r"\bC\.?\s?S\.?\s?E\.?\b|computer science|software engineering|ict", re.I)

# Best-effort deadline sniff from the headline/snippet. Often finds nothing --
# that's fine; the card just shows the posted date instead.
DEADLINE_RE = re.compile(
    r"(?:deadline|last date|apply by|closing date|application deadline)\D{0,15}"
    r"(\d{1,2}\s*(?:st|nd|rd|th)?[\s\-/]*(?:[A-Za-z]{3,9}|\d{1,2})[\s\-/,]*\d{2,4})",
    re.I,
)

MAX_ITEMS = 50
TIMEOUT = 30


def read_feed_urls():
    raw = os.environ.get("FEED_URLS", "")
    urls = [u.strip() for u in re.split(r"[,\n]", raw) if u.strip()]
    if not urls and os.path.exists("feeds.txt"):
        with open("feeds.txt", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line and not line.startswith("#"):
                    urls.append(line)
    return urls


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "notice-board-bot/1.0"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read()


def clean(text):
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text)        # strip the <b> tags Google adds around matches
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def real_url(link):
    # Google Alerts wraps links: https://www.google.com/url?...&url=REAL_URL&...
    if not link:
        return ""
    m = re.search(r"[?&]url=([^&]+)", link)
    return urllib.parse.unquote(m.group(1)) if m else link


def host(url):
    m = re.match(r"https?://([^/]+)", url or "")
    h = m.group(1) if m else ""
    return h[4:] if h.startswith("www.") else h


def sniff_deadline(text):
    m = DEADLINE_RE.search(text or "")
    return m.group(1).strip() if m else None


def parse_feed(data):
    items = []
    root = ET.fromstring(data)
    for e in root.findall(ATOM + "entry"):
        title = clean(e.findtext(ATOM + "title"))
        link_el = e.find(ATOM + "link")
        url = real_url(link_el.get("href") if link_el is not None else "")
        published = (e.findtext(ATOM + "published") or e.findtext(ATOM + "updated") or "")[:10]
        snippet = clean(e.findtext(ATOM + "content") or e.findtext(ATOM + "summary"))
        blob = title + " " + snippet
        relevant = ROLE.search(blob) or (FIELD.search(blob) and JOB_INTENT.search(blob))
        if not url or not relevant:
            continue
        items.append({
            "title": title,
            "url": url,
            "source": host(url),
            "published": published,
            "deadline": sniff_deadline(blob),
            "snippet": snippet[:240],
        })
    return items


def main():
    urls = read_feed_urls()
    if not urls:
        sys.stderr.write("No feed URLs. Set FEED_URLS or create feeds.txt.\n")
        # Still write an empty-but-valid file so the board shows a clean state.
        write([], note="no feed configured")
        return 0

    seen, items = set(), []
    for url in urls:
        try:
            found = parse_feed(fetch(url))
            print(f"  {len(found):>3} items from {url[:60]}...")
        except Exception as exc:  # one bad feed shouldn't kill the run
            print(f"  !! failed {url[:60]}...: {exc}")
            continue
        for it in found:
            if it["url"] in seen:
                continue
            seen.add(it["url"])
            items.append(it)

    items.sort(key=lambda it: it.get("published") or "", reverse=True)
    items = items[:MAX_ITEMS]
    write(items)
    print(f"Wrote notices.json with {len(items)} items.")
    return 0


def write(items, note=None):
    payload = {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "count": len(items),
        "items": items,
    }
    if note:
        payload["note"] = note
    with open("notices.json", "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    raise SystemExit(main())
