# Bulk YouTube transcripts

Download the transcripts of a whole YouTube channel, playlist or search as Markdown files, one per video, with chapters and timestamps.
I use it to feed lectures and talks into an LLM or a RAG index.

The transcripts come from my [YouTube Transcript & Subtitles Scraper](https://apify.com/heyitsgautham/youtube-transcript-scraper) on Apify.
I built it, and it's paid per result, $3 per 1,000 transcripts.
Videos without captions, and videos that fail, cost nothing.
Listing a channel, playlist or search is free too.

## Why a hosted scraper

The open-source youtube-transcript-api library works fine on a laptop.
Deploy it to a cloud server and calls start dying with `RequestBlocked` or `IpBlocked`, because YouTube blocks most IP ranges that belong to cloud providers.
I measured how often that happens, and what fixes it, [in a dev.to post](https://dev.to/heyitsgautham/youtube-transcript-api-requestblocked-and-ipblocked-on-cloud-servers-and-what-actually-fixes-it-41da).
If your job runs on a server, or you want hundreds of videos without babysitting retries, the scraper does the fetching on Apify and hands you JSON.

## The script

`channel_to_markdown.py` takes a channel, a playlist or a search, and writes:

- one `.md` file per video, named by date and title, with the title, channel, date, URL, duration and caption type on top, then a heading per YouTube chapter and a `[m:ss]` stamp per paragraph
- `index.csv`, one row per video with its status, word count and file name

```bash
pip install -r requirements.txt
export APIFY_TOKEN=your_token_here

python channel_to_markdown.py https://www.youtube.com/@3blue1brown --max 3
python channel_to_markdown.py "https://www.youtube.com/playlist?list=PL..." --out lectures/
python channel_to_markdown.py --search "how transformers work" --max 5
```

My run on 26 Oct 2026 took the 3 newest 3Blue1Brown videos.

```
Fetching up to 3 videos, at most $0.009. 0 already saved in transcripts/
Saved 3 new transcripts, 25,810 words, to transcripts/
  ok            Nbwv5wHQoj0  The last IMO problem AI could not solve
  ok            GlYgs6v2YfU  But what is cross-entropy? | Compression is Intelligence Part 2
  ok            LKrwhjOI8Nc  There's never been a better time to go into math
```

```
transcripts/
  2026-07-16-but-what-is-cross-entropy-compression-is-intelligence-part-2-GlYgs6v2YfU.md
  2026-09-18-the-last-imo-problem-ai-could-not-solve-Nbwv5wHQoj0.md
  2026-10-16-there-s-never-been-a-better-time-to-go-into-math-LKrwhjOI8Nc.md
  index.csv
```

The top of the cross-entropy file, which has 10 chapters:

```markdown
# But what is cross-entropy? | Compression is Intelligence Part 2
Channel: 3Blue1Brown
Published: 2026-07-16T11:56:04Z
URL: https://www.youtube.com/watch?v=GlYgs6v2YfU
Duration: 33:51
Captions: en

## Language trees and zipping [0:00]

[0:00] There's a kind of wild paper from 2002 called Language Trees and Zipping, which shows how you can find structure between languages just by using very general file compression. ...
```

Run it again into the same folder and it adds the new videos, leaving files from earlier runs alone.
The scraper still fetches and charges every video it lists, so set `--max` close to the number of new uploads.
The script caps each run's charge at `--max` times $0.003.

## Quick start in Python

```python
import os
from apify_client import ApifyClient

client = ApifyClient(os.environ["APIFY_TOKEN"])
run = client.actor("heyitsgautham/youtube-transcript-scraper").call(run_input={
    "videos": ["https://youtu.be/jNQXAC9IVRw", "dQw4w9WgXcQ"],
    "language": "en",
    "includeTimestamps": True,
})
for video in client.dataset(run.default_dataset_id).iterate_items():
    print(video["status"], video.get("title"), video.get("wordCount"))
```

With `includeTimestamps` on, each row also has `segments`, a list of `{"start", "duration", "text"}`.

## Quick start with curl

`fields` trims the response to the columns you want.

```bash
curl -X POST "https://api.apify.com/v2/acts/heyitsgautham~youtube-transcript-scraper/run-sync-get-dataset-items?fields=videoId,title,language,wordCount,transcript" \
  -H "Authorization: Bearer $APIFY_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"videos": ["https://youtu.be/jNQXAC9IVRw"], "includeTimestamps": false}'
```

What came back when I ran it:

```json
[{
  "videoId": "jNQXAC9IVRw",
  "title": "Me at the zoo",
  "language": "en",
  "wordCount": 39,
  "transcript": "All right, so here we are, in front of the elephants the cool thing about these guys is that they have really... really really long trunks and that's cool (baaaaaaaaaaahhh!!) and that's pretty much all there is to say"
}]
```

## Inputs

| Input | What it takes |
|---|---|
| `videos` | Watch, youtu.be, Shorts, embed and live links, or bare 11-character IDs |
| `channelsAndPlaylists` | `@handle`, `/channel/UC...`, `/c/name` and `/user/name` links, playlist links, or bare IDs. Channels go newest first |
| `searchQueries` | YouTube searches, each giving its top videos in YouTube's order |
| `maxVideosPerSource` | Videos per channel, playlist or search. 100 by default, `0` means all, up to 20,000 |
| `language` | Preferred caption language. Human captions come first, then auto-generated, then the video's original captions |
| `includeVideoDetails` | Views, likes, comment count, tags, description and chapters, at no extra cost |
| `outputFormats` | Any of `text`, `llm`, `srt`, `vtt` and `chunks` (RAG chunks split by chapter), at no extra cost |

## Price

| Apify tier | Per 1,000 transcripts |
|---|---|
| No discount | $3.00 |
| Bronze | $2.70 |
| Silver | $2.40 |
| Gold | $2.10 |

No start fee.
In the final test on 16 Oct 2026, 88 videos from links, channels, playlists and searches went in, and all 87 that exist returned a transcript with every format, in 73 seconds.

## Limits

- It reads YouTube's own captions and doesn't run speech-to-text. A video with no captions returns a free `no_transcript` row.
- Live streams get captions only after they end.
- A video met twice in one run is fetched and charged once.
- Use transcripts in ways that respect the rights of the video owners.

## License

MIT for the code here.
