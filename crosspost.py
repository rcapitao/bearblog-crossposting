#!/usr/bin/env python3
"""Crossposts new Bear Blog posts to Mastodon and Bluesky.

Reads the blog's RSS feed, compares it against a local state file of
already-posted entries, and publishes any new posts to the configured
networks. Designed to run on a schedule (e.g. GitHub Actions cron).
"""
import json
import os
import re
import sys
from pathlib import Path

import feedparser
import requests

STATE_FILE = Path(__file__).parent / "state.json"

FEED_URL = os.environ["FEED_URL"]

MASTODON_BASE_URL = os.environ.get("MASTODON_BASE_URL")
MASTODON_ACCESS_TOKEN = os.environ.get("MASTODON_ACCESS_TOKEN")

BLUESKY_HANDLE = os.environ.get("BLUESKY_HANDLE")
BLUESKY_APP_PASSWORD = os.environ.get("BLUESKY_APP_PASSWORD")


def load_state() -> set:
    if STATE_FILE.exists():
        return set(json.loads(STATE_FILE.read_text()))
    return set()


def save_state(posted_ids: set) -> None:
    STATE_FILE.write_text(json.dumps(sorted(posted_ids), indent=2) + "\n")


def fetch_new_entries(posted_ids: set):
    feed = feedparser.parse(FEED_URL)
    if feed.bozo and not feed.entries:
        raise RuntimeError(f"Failed to parse feed: {feed.bozo_exception}")

    new_entries = [
        entry for entry in feed.entries if entry.link not in posted_ids
    ]
    # Oldest first, so posting order matches publish order.
    return list(reversed(new_entries))


def get_meta_description(entry) -> str:
    summary = getattr(entry, "summary", "") or ""
    return re.sub(r"<[^>]+>", "", summary).strip()


def build_message(entry) -> str:
    first_line = f"{entry.title}: {entry.link}"
    description = get_meta_description(entry)
    if not description:
        return first_line
    return f"{first_line}\n\n{description}"


def post_to_mastodon(message: str) -> None:
    if not (MASTODON_BASE_URL and MASTODON_ACCESS_TOKEN):
        print("Mastodon not configured, skipping.")
        return

    response = requests.post(
        f"{MASTODON_BASE_URL}/api/v1/statuses",
        headers={"Authorization": f"Bearer {MASTODON_ACCESS_TOKEN}"},
        data={"status": message, "visibility": "public"},
        timeout=30,
    )
    response.raise_for_status()
    print("Posted to Mastodon.")


def bluesky_login() -> dict:
    response = requests.post(
        "https://bsky.social/xrpc/com.atproto.server.createSession",
        json={"identifier": BLUESKY_HANDLE, "password": BLUESKY_APP_PASSWORD},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def post_to_bluesky(entry, message: str) -> None:
    if not (BLUESKY_HANDLE and BLUESKY_APP_PASSWORD):
        print("Bluesky not configured, skipping.")
        return

    session = bluesky_login()

    import datetime

    link_prefix = f"{entry.title}: "
    byte_start = len(link_prefix.encode())
    byte_end = byte_start + len(entry.link.encode())

    record = {
        "$type": "app.bsky.feed.post",
        "text": message,
        "createdAt": datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%S.%fZ"
        ),
        "facets": [
            {
                "index": {"byteStart": byte_start, "byteEnd": byte_end},
                "features": [
                    {"$type": "app.bsky.richtext.facet#link", "uri": entry.link}
                ],
            }
        ],
    }

    response = requests.post(
        "https://bsky.social/xrpc/com.atproto.repo.createRecord",
        headers={"Authorization": f"Bearer {session['accessJwt']}"},
        json={
            "repo": session["did"],
            "collection": "app.bsky.feed.post",
            "record": record,
        },
        timeout=30,
    )
    response.raise_for_status()
    print("Posted to Bluesky.")


def main() -> int:
    posted_ids = load_state()
    new_entries = fetch_new_entries(posted_ids)

    if not new_entries:
        print("No new posts.")
        return 0

    if os.environ.get("SEED_ONLY") == "1":
        print(f"Seeding state with {len(new_entries)} existing post(s), not posting.")
        posted_ids.update(entry.link for entry in new_entries)
        save_state(posted_ids)
        return 0

    for entry in new_entries:
        message = build_message(entry)
        print(f"Crossposting: {entry.title}")
        try:
            post_to_mastodon(message)
            post_to_bluesky(entry, message)
        except requests.HTTPError as exc:
            print(f"Failed to crosspost '{entry.title}': {exc}", file=sys.stderr)
            continue
        posted_ids.add(entry.link)

    save_state(posted_ids)
    return 0


if __name__ == "__main__":
    sys.exit(main())
