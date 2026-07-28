from unittest.mock import patch
import feedparser
from src.fetch import fetch_entries, fetch_all

SAMPLE_RSS = """<?xml version="1.0"?>
<rss version="2.0">
<channel>
  <title>Sample Feed</title>
  <item>
    <title>Post One</title>
    <link>https://example.com/post-1</link>
    <guid>https://example.com/post-1</guid>
    <description>Body of post one.</description>
  </item>
  <item>
    <title>Post Two</title>
    <link>https://example.com/post-2</link>
    <guid>https://example.com/post-2</guid>
    <description>Body of post two.</description>
  </item>
</channel>
</rss>
"""

BAD_RSS = "not xml at all"


def test_fetch_entries_parses_items():
    parsed = feedparser.parse(SAMPLE_RSS)
    with patch("src.fetch.feedparser.parse", return_value=parsed):
        entries = fetch_entries("https://example.com/feed", "Sample Author")

    assert len(entries) == 2
    assert entries[0] == {
        "id": "https://example.com/post-1",
        "source": "Sample Author",
        "title": "Post One",
        "link": "https://example.com/post-1",
        "content": "Body of post one.",
    }


def test_fetch_all_skips_failing_source_and_keeps_others():
    good_parsed = feedparser.parse(SAMPLE_RSS)

    def fake_parse(url):
        if url == "https://good.example/feed":
            return good_parsed
        raise RuntimeError("network error")

    with patch("src.fetch.feedparser.parse", side_effect=fake_parse):
        entries = fetch_all([
            {"name": "Good Author", "feed_url": "https://good.example/feed"},
            {"name": "Broken Author", "feed_url": "https://broken.example/feed"},
        ])

    assert len(entries) == 2
    assert all(e["source"] == "Good Author" for e in entries)
