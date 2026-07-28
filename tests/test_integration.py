"""End-to-end test of run() with mocks placed only at the network boundary.

Unlike tests/test_main.py (which mocks src.main's own collaborators), this test
exercises the real src.fetch → src.llm → src.digest → src.telegram chain and
only replaces feedparser.parse (RSS layer) and requests.post (Gemini + Telegram
HTTP layer). It is what would have caught the missing HTML escaping.
"""

import json
from unittest.mock import MagicMock, patch

import feedparser

from src.main import run

SOURCES = [{"name": "Emily Kramer & Kathleen Estreich", "feed_url": "https://mkt1.example/feed"}]
FALLBACK_SOURCES = [{"name": "Fallback A", "feed_url": "https://fb.example/feed"}]

FEED_XML = """<?xml version="1.0"?>
<rss version="2.0">
<channel>
  <title>MKT1</title>
  <item>
    <title>Growth &amp; retention under &lt;$1k budget</title>
    <link>https://mkt1.example/post-1</link>
    <guid>https://mkt1.example/post-1</guid>
    <description>How to grow with almost no money.</description>
  </item>
  <item>
    <title>How we hired our VP of Sales</title>
    <link>https://mkt1.example/post-2</link>
    <guid>https://mkt1.example/post-2</guid>
    <description>A hiring story, not marketing.</description>
  </item>
  <item>
    <title>Positioning &gt; features</title>
    <link>https://mkt1.example/post-3</link>
    <guid>https://mkt1.example/post-3</guid>
    <description>Why positioning beats features.</description>
  </item>
</channel>
</rss>
"""

GEMINI_PAYLOADS = [
    {
        "relevant": True,
        "summary": "Рост при бюджете <$1k & без рекламы.",
        "takeaway": "Стройте дистрибуцию в открытую.",
    },
    {"relevant": False, "summary": "", "takeaway": ""},
    {
        "relevant": True,
        "summary": "Позиционирование > фич.",
        "takeaway": "Сначала опишите позиционирование, потом функции.",
    },
]


def _gemini_response(payload: dict) -> MagicMock:
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {"candidates": [{"content": {"parts": [{"text": json.dumps(payload)}]}}]}
    return resp


def _telegram_response() -> MagicMock:
    resp = MagicMock()
    resp.json.return_value = {"ok": True}
    return resp


def test_end_to_end_fetch_llm_telegram_with_real_modules(tmp_path):
    state_path = str(tmp_path / "state.json")
    parsed_feed = feedparser.parse(FEED_XML)
    assert not parsed_feed.get("bozo")

    gemini_calls = []
    telegram_calls = []
    pending_gemini = list(GEMINI_PAYLOADS)

    # src.llm and src.telegram share the same `requests` module object, so a
    # single mock at the HTTP boundary dispatches on the destination URL.
    def fake_post(url, **kwargs):
        if "generativelanguage.googleapis.com" in url:
            gemini_calls.append((url, kwargs))
            return _gemini_response(pending_gemini.pop(0))
        if "api.telegram.org" in url:
            telegram_calls.append((url, kwargs))
            return _telegram_response()
        raise AssertionError(f"unexpected HTTP call to {url}")

    with patch("src.fetch.feedparser.parse", return_value=parsed_feed), \
         patch("requests.post", side_effect=fake_post):
        run(state_path, SOURCES, FALLBACK_SOURCES, "gk", "tok", "@chan")

    # All three entries went through the real Gemini call path
    assert len(gemini_calls) == 3
    # Only one Telegram message (well under the 4096-char chunk limit)
    assert len(telegram_calls) == 1

    url, kwargs = telegram_calls[0]
    body = kwargs["json"]
    assert url == "https://api.telegram.org/bottok/sendMessage"
    assert body["chat_id"] == "@chan"
    assert body["parse_mode"] == "HTML"

    text = body["text"]
    # Source name and title arriving from RSS are HTML-escaped
    assert "Emily Kramer &amp; Kathleen Estreich" in text
    assert "Growth &amp; retention under &lt;$1k budget" in text
    assert "Positioning &gt; features" in text
    # Gemini-generated Russian text is escaped too
    assert "Рост при бюджете &lt;$1k &amp; без рекламы." in text
    assert "Позиционирование &gt; фич." in text
    # Nothing unescaped survived that could trip Telegram's HTML parser
    assert "<" not in text and ">" not in text
    # The irrelevant (hiring) item was filtered out by the real LLM branch
    assert "VP of Sales" not in text
    # Two items in the digest, joined by the real separator
    assert text.count("🔹") == 2
    assert "\n\n---\n\n" in text

    from src.state import is_seen, load_state

    state = load_state(state_path)
    assert is_seen(state, "https://mkt1.example/post-1")
    assert is_seen(state, "https://mkt1.example/post-2")
    assert is_seen(state, "https://mkt1.example/post-3")
