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

Note on the alert queries themselves: do NOT use the site: operator.
Google Alerts almost never fires for site-restricted queries, so those feeds
stay permanently empty even though plain web search finds plenty of matches.
"""

import os
import re
import sys
import json
import html
import time
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from xml.etree import ElementTree as ET

ATOM = "{http://www.w3.org/2005/Atom}"

# Keep an entry only if it looks like an actual job posting, not news that
# merely mentions a CSE department or quotes a lecturer.
#
# Rule: a hiring ROLE word AND a JOB_INTENT word must BOTH appear.
# ROLE on its own is far too weak -- "lecturer" and "faculty" turn up in
# ordinary news constantly ("CUET lecturer arrested", "faculty members
# protest"), and on a labelled sample that alone let through half the noise.
# Bare "professor" is deliberately excluded: news quotes professors all day.
ROLE = re.compile(
    r"lecturer|senior lecturer|assistant professor|associate professor|"
    r"faculty|adjunct|teaching position|প্রভাষক|সহকারী অধ্যাপক", re.I)

# "appl" not "apply" -- job ads say "Applications are invited", and
# apply/applications diverge at the fourth letter, so "apply" never fired.
JOB_INTENT = re.compile(
    r"recruit|vacan|circular|appl|invit|hiring|appointment|position|career|"
    r"walk-?in|wanted|opening|নিয়োগ|বিজ্ঞপ্তি", re.I)

# \bict\b, not bare "ict" -- otherwise it matches inside District, conflict,
# verdict, strict, prediction.
FIELD = re.compile(
    r"\bC\.?\s?S\.?\s?E\.?\b|computer science|software engineering|\bict\b", re.I)

# Best-effort deadline sniff from the headline/snippet. Often finds nothing --
# that's fine; the card just shows the posted date instead.
DEADLINE_RE = re.compile(
    r"(?:deadline|last date|apply by|closing date|application deadline)\D{0,15}"
    r"(\d{1,2}\s*(?:st|nd|rd|th)?[\s\-/]*(?:[A-Za-z]{3,9}|\d{1,2})[\s\-/,]*\d{2,4})",
    re.I,
)

MAX_ITEMS = 50
TIMEOUT = 30
RETRIES = 2          # one retry covers the usual transient blip


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
    last = None
    for attempt in range(RETRIES):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "notice-board-bot/1.0"})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                return resp.read()
        except Exception as exc:
            last = exc
            if attempt + 1 < RETRIES:
                time.sleep(3)
    raise last


def clean(text):
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text)        # strip the <b> tags Google adds around matches
