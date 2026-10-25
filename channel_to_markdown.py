"""Save the transcripts of a YouTube channel, playlist or search as Markdown files.

Each video becomes one .md file with the title, channel, date, URL and a
timestamped transcript split by chapter, ready to drop into an LLM, a notes
app or a RAG index. An index.csv lists every video and what happened to it.

Usage:
    export APIFY_TOKEN=...
    python channel_to_markdown.py https://www.youtube.com/@TED --max 20
    python channel_to_markdown.py "PLxxxxxxxx" --out lectures/
    python channel_to_markdown.py --search "how transformers work" --max 5

Run it again with the same folder and it adds new videos to the folder and
the index, leaving the files it saved before alone. The scraper still fetches
and charges every video it lists, so keep --max near the number of new uploads.
"""

import argparse
import csv
import os
import re
import sys
from decimal import Decimal
from pathlib import Path

from apify_client import ApifyClient

ACTOR = "heyitsgautham/youtube-transcript-scraper"
PRICE_PER_TRANSCRIPT = Decimal("0.003")
INDEX_FIELDS = ["videoId", "status", "publishedAt", "title", "channel", "durationSeconds", "wordCount", "file", "message"]


def slug(text, limit=60):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:limit] or "untitled"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("source", nargs="?", help="channel URL or @handle, playlist URL or PL... ID")
    parser.add_argument("--search", help="a YouTube search instead of a channel or playlist")
    parser.add_argument("--max", type=int, default=20, help="newest videos to take from the source (default 20)")
    parser.add_argument("--language", default="en", help="preferred caption language (default en)")
    parser.add_argument("--out", default="transcripts", help="output folder (default transcripts/)")
    args = parser.parse_args()

    if not (args.source or args.search):
        parser.error("give a channel or playlist, or --search")
    token = os.environ.get("APIFY_TOKEN")
    if not token:
        sys.exit("Set APIFY_TOKEN first. Get one at https://console.apify.com/settings/integrations")

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    index_path = out / "index.csv"
    done = set()
    if index_path.exists():
        with index_path.open(encoding="utf-8") as f:
            done = {row["videoId"] for row in csv.DictReader(f) if row["status"] == "ok"}

    run_input = {
        "channelsAndPlaylists": [args.source] if args.source else [],
        "searchQueries": [args.search] if args.search else [],
        "maxVideosPerSource": args.max,
        "language": args.language,
        "includeTimestamps": False,
        "includeVideoDetails": True,
        "outputFormats": ["llm"],
    }
    # Listing is free and only transcripts are charged, so this is the most a run can cost.
    cap = PRICE_PER_TRANSCRIPT * args.max
    print(f"Fetching up to {args.max} videos, at most ${cap:.3f}. {len(done)} already saved in {out}/")

    client = ApifyClient(token)
    run = client.actor(ACTOR).call(run_input=run_input, max_total_charge_usd=cap, logger=None)
    if run is None or run.status != "SUCCEEDED":
        sys.exit(f"Run did not succeed: {run.status if run else 'no run'}")

    new_rows = []
    for item in client.dataset(run.default_dataset_id).iterate_items():
        vid = item.get("videoId")
        if vid in done:
            continue
        row = {k: item.get(k) for k in INDEX_FIELDS}
        if item.get("status") == "ok":
            name = f"{(item.get('publishedAt') or '')[:10]}-{slug(item['title'])}-{vid}.md"
            (out / name).write_text(item["llmText"], encoding="utf-8")
            row["file"] = name
        new_rows.append(row)

    write_header = not index_path.exists()
    with index_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=INDEX_FIELDS)
        if write_header:
            writer.writeheader()
        writer.writerows(new_rows)

    saved = [r for r in new_rows if r["status"] == "ok"]
    print(f"Saved {len(saved)} new transcripts, {sum(r['wordCount'] or 0 for r in saved):,} words, to {out}/")
    for r in new_rows:
        print(f"  {r['status']:13} {r['videoId']}  {(r['title'] or r['message'] or '')[:70]}")


if __name__ == "__main__":
    main()
