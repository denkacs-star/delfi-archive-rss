#!/usr/bin/env python3
"""Generate an RSS 2.0 feed from the archive.ph snapshot list for rus.delfi.lv.

archive.ph (archive.today) keeps a running list of every snapshot taken of
https://rus.delfi.lv/ at https://archive.ph/rus.delfi.lv . The list page has
no feed of its own, so this script scrapes the listing (title, snapshot
permalink, snapshot date, original article URL), then fetches each snapshot
page once and extracts the full article text with trafilatura. Extracted
fulltext is cached in cache.json next to this script so re-runs don't
re-fetch snapshots archive.ph has already rate-limited us for.

Needs trafilatura + lxml (see venv/ — run via lauf.sh, not bare python3).
"""

from __future__ import annotations

import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from email.utils import format_datetime

import trafilatura

SOURCE = "https://archive.ph/rus.delfi.lv"
FEED_URL = "https://denkacs-star.github.io/delfi-archive-rss/feed.xml"
SITE_URL = "https://denkacs-star.github.io/delfi-archive-rss/"

MAX_ITEMS = 60
EXCERPT_LEN = 400

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_FILE = os.path.join(SCRIPT_DIR, "cache.json")

# Pause between per-snapshot fetches so we don't hammer archive.ph.
SNAPSHOT_FETCH_DELAY = 4

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ru,en;q=0.8,de;q=0.6",
}

# archive.ph rate-limits aggressively (HTTP 429); retry with backoff.
RETRY_DELAYS = [15, 60, 180]

MONTHS = {
    m: i + 1
    for i, m in enumerate(
        "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
    )
}


def fetch(url: str, delays: list[int] | None = None) -> str:
    """GET url. `delays` = backoff schedule for HTTP 429 (default RETRY_DELAYS)."""
    if delays is None:
        delays = RETRY_DELAYS
    req = urllib.request.Request(url, headers=HEADERS)
    last_exc: Exception | None = None
    for attempt, delay in enumerate([0] + delays):
        if delay:
            print(f"retry {attempt} after {delay}s (last error: {last_exc})", file=sys.stderr)
            time.sleep(delay)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read()
            return raw.decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            last_exc = exc
            if exc.code != 429:
                raise
        except urllib.error.URLError as exc:
            last_exc = exc
    raise last_exc


def clean(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return html.unescape(text).strip()


def parse_date(text: str) -> datetime:
    # e.g. "17 Sep 2026 10:50"
    day, mon, year, time_ = text.split()
    hour, minute = time_.split(":")
    return datetime(
        int(year), MONTHS[mon], int(day), int(hour), int(minute), tzinfo=timezone.utc
    )


def parse_entries(page: str):
    """Yield entry dicts from an archive.ph listing page."""
    rows = re.split(r'<div id="row\d+"', page)[1:]
    for row in rows:
        date_m = re.search(
            r'text-align:right">(\d{1,2} \w{3} \d{4} \d{2}:\d{2})</div>', row
        )
        title_link_m = re.search(
            r'font-size:16px;word-break:break-word" href="(https://archive\.ph/[^"]+)">(.*?)</a>',
            row,
            re.S,
        )
        orig_m = re.search(r'href="https://archive\.ph/(https?://[^"]+)"', row)
        if not (date_m and title_link_m and orig_m):
            continue

        yield {
            "date": parse_date(date_m.group(1)),
            "archive_link": title_link_m.group(1),
            "title": clean(title_link_m.group(2)),
            "original_url": html.unescape(orig_m.group(1)),
        }


def load_cache() -> dict:
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, encoding="utf-8") as fh:
            return json.load(fh)
    return {}


def save_cache(cache: dict) -> None:
    with open(CACHE_FILE, "w", encoding="utf-8") as fh:
        json.dump(cache, fh, ensure_ascii=False, indent=2, sort_keys=True)


def excerpt_from_html(body_html: str, length: int = EXCERPT_LEN) -> str:
    text = re.sub(r"<[^>]+>", " ", body_html)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= length:
        return text
    return text[:length].rsplit(" ", 1)[0] + "…"


def extract_article(page: str) -> dict | None:
    body_html = trafilatura.extract(
        page,
        include_comments=False,
        include_tables=False,
        output_format="html",
    )
    if not body_html:
        return None

    # Drop the leading <h1> — the RSS <title> already carries it.
    body_html = re.sub(r"^\s*<html>\s*<body>\s*", "", body_html)
    body_html = re.sub(r"^\s*<h1>.*?</h1>\s*", "", body_html, count=1, flags=re.S)
    body_html = re.sub(r"\s*</body>\s*</html>\s*$", "", body_html).strip()

    meta = trafilatura.extract_metadata(page)
    return {
        "body_html": body_html,
        "excerpt": excerpt_from_html(body_html),
        "author": meta.author if meta and meta.author else None,
    }


def fetch_fulltext(archive_link: str) -> dict | None:
    """Fetch one archive.ph snapshot (single attempt) and extract the article.

    Raises on network/HTTP failure so the caller can tell "transient error,
    retry tomorrow" apart from "fetched fine, just nothing to extract".
    """
    result = extract_article(fetch(archive_link, delays=[]))
    if result:
        result["source"] = "archive"
    return result


def fetch_original(original_url: str) -> dict | None:
    """Fallback: article start from the live page (paywalled -> teaser only)."""
    result = extract_article(fetch(original_url, delays=[]))
    if result:
        result["source"] = "original"
    return result


def collect():
    page = fetch(SOURCE)
    items = list(parse_entries(page))
    # newest first, de-dup by archive_link just in case
    seen = set()
    result = []
    for it in sorted(items, key=lambda a: a["date"], reverse=True):
        if it["archive_link"] in seen:
            continue
        seen.add(it["archive_link"])
        result.append(it)
    result = result[:MAX_ITEMS]

    cache = load_cache()
    dirty = False
    # Set on the first HTTP 429 (archive.ph CAPTCHA wall): stop asking for
    # snapshots for the rest of this run instead of burning minutes on retries.
    archive_blocked = False
    for it in result:
        link = it["archive_link"]
        have_cached = link in cache
        cached = cache.get(link)
        # Wanted from the archive: never fetched, or only the paywalled
        # teaser from the original so far (upgrade once archive.ph answers).
        wants_archive = not have_cached or (
            cached is not None and cached.get("source") == "original"
        )

        if wants_archive and not archive_blocked:
            print(f"fetching fulltext: {it['title'][:60]}", file=sys.stderr)
            try:
                fulltext = fetch_fulltext(link)
            except urllib.error.HTTPError as exc:
                if exc.code == 429:
                    archive_blocked = True
                    print("warn: archive.ph answers 429 (CAPTCHA) – skipping "
                          "further snapshots this run", file=sys.stderr)
                else:
                    print(f"warn: fetching {link} failed: {exc}", file=sys.stderr)
            except Exception as exc:  # noqa: BLE001 - transient, retry tomorrow
                print(f"warn: fetching {link} failed: {exc}", file=sys.stderr)
            else:
                # Cache "nothing extractable" too (stable) — but never let it
                # overwrite a teaser we already have.
                if fulltext is not None or not have_cached:
                    cache[link] = fulltext
                    dirty = True
                    cached = fulltext
            time.sleep(SNAPSHOT_FETCH_DELAY)

        if not cached and not have_cached and link not in cache:
            # No archive text (blocked/failed): take the start of the article
            # from the live page so the feed item isn't empty.
            try:
                fallback = fetch_original(it["original_url"])
            except Exception as exc:  # noqa: BLE001
                print(f"warn: original {it['original_url']} failed: {exc}", file=sys.stderr)
            else:
                if fallback:
                    cache[link] = fallback
                    dirty = True
                    cached = fallback
            time.sleep(1)

        if cached:
            it.update(cached)

    if dirty:
        save_cache(cache)

    return result


def build_rss(items) -> str:
    now = format_datetime(datetime.now(tz=timezone.utc))
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom" '
        'xmlns:content="http://purl.org/rss/1.0/modules/content/">',
        "  <channel>",
        "    <title>rus.delfi.lv – archive.ph Snapshots</title>",
        f"    <link>{SOURCE}</link>",
        "    <description>Inoffizieller Feed der archive.ph-Archivkopien von "
        "rus.delfi.lv – jeder Eintrag ist ein neuer Snapshot der Original-"
        "Website, inklusive Volltext.</description>",
        "    <language>ru</language>",
        f"    <lastBuildDate>{now}</lastBuildDate>",
        "    <generator>delfi-archive-rss (github.com/denkacs-star/delfi-archive-rss)</generator>",
        f'    <atom:link href="{FEED_URL}" rel="self" type="application/rss+xml"/>',
    ]
    for a in items:
        title = html.escape(a["title"])
        link = html.escape(a["archive_link"])
        orig = html.escape(a["original_url"])
        body_html = a.get("body_html")
        if body_html:
            desc = html.escape(a["excerpt"])
        else:
            desc = html.escape(f"Archiv-Snapshot von {a['original_url']}")

        parts.append("    <item>")
        parts.append(f"      <title>{title}</title>")
        parts.append(f"      <link>{link}</link>")
        parts.append(f'      <guid isPermaLink="true">{link}</guid>')
        parts.append(f"      <pubDate>{format_datetime(a['date'])}</pubDate>")
        if a.get("author"):
            parts.append(f"      <author>{html.escape(a['author'])}</author>")
        parts.append(f"      <description>{desc}</description>")
        parts.append(f"      <comments>{orig}</comments>")
        if body_html:
            notice = ""
            if a.get("source") == "original":
                notice = (
                    "<p><strong>Nur der Artikelanfang (Paywall).</strong> "
                    "Der Volltext wird nachgeladen, sobald archive.ph den "
                    "Snapshot wieder ausliefert.</p>"
                )
            footer = (
                f'<p><em>Original: <a href="{orig}">{orig}</a> · '
                f'Archiv-Snapshot: <a href="{link}">{link}</a></em></p>'
            )
            parts.append(
                f"      <content:encoded><![CDATA[{notice}{body_html}{footer}]]></content:encoded>"
            )
        parts.append("    </item>")
    parts.append("  </channel>")
    parts.append("</rss>")
    return "\n".join(parts) + "\n"


INDEX_HTML = """<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>rus.delfi.lv Archiv-RSS</title>
<link rel="alternate" type="application/rss+xml" title="rus.delfi.lv archive.ph Snapshots" href="feed.xml">
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 42rem; margin: 3rem auto;
         padding: 0 1rem; line-height: 1.5; color: #1a1a1a; }}
  a {{ color: #0645ad; }}
  code {{ background: #f2f2f2; padding: .1rem .35rem; border-radius: 4px; }}
  .muted {{ color: #666; font-size: .9rem; }}
  ul {{ padding-left: 1.2rem; }}
</style>
</head>
<body>
<h1>rus.delfi.lv – Archiv-RSS</h1>
<p>Inoffizieller RSS-Feed der <a href="{source}">archive.ph-Snapshot-Liste</a>
von <a href="https://rus.delfi.lv/">rus.delfi.lv</a>, inklusive Artikel-Volltext.
Jeder neue Snapshot wird als Eintrag im Feed geführt. Wird täglich automatisch
aktualisiert.</p>
<p><strong>Feed-Adresse (in den RSS-Reader kopieren):</strong><br>
<code>{feed_url}</code></p>
<p><a href="feed.xml">→ feed.xml öffnen</a></p>
<h2>Aktuell im Feed ({count} Snapshots)</h2>
<ul>
{items}
</ul>
<p class="muted">Zuletzt gebaut: {built} · Quelle: archive.ph ·
<a href="https://github.com/denkacs-star/delfi-archive-rss">Quellcode &amp; Automatik auf GitHub</a></p>
</body>
</html>
"""


def build_index(items) -> str:
    lis = "\n".join(
        '<li><a href="{link}">{title}</a> '
        '<span class="muted">– {date}</span></li>'.format(
            link=html.escape(a["archive_link"]),
            title=html.escape(a["title"]),
            date=a["date"].strftime("%d.%m.%Y %H:%M"),
        )
        for a in items
    )
    return INDEX_HTML.format(
        source=SOURCE,
        feed_url=FEED_URL,
        count=len(items),
        items=lis,
        built=datetime.now(tz=timezone.utc).strftime("%d.%m.%Y %H:%M UTC"),
    )


def main():
    outdir = sys.argv[1] if len(sys.argv) > 1 else "docs"
    os.makedirs(outdir, exist_ok=True)
    items = collect()
    if not items:
        print("error: no entries parsed – aborting", file=sys.stderr)
        sys.exit(1)
    with open(os.path.join(outdir, "feed.xml"), "w", encoding="utf-8") as fh:
        fh.write(build_rss(items))
    with open(os.path.join(outdir, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(build_index(items))
    n_full = sum(1 for a in items if a.get("body_html"))
    print(f"wrote {len(items)} items ({n_full} with fulltext) to {outdir}/feed.xml")


if __name__ == "__main__":
    main()
