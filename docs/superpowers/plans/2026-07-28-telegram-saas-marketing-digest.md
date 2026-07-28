# Telegram SaaS Marketing Digest Bot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python bot that runs 3×/day via GitHub Actions, checks RSS feeds from 7 SaaS-marketing authors (falling back to a pool of $0-budget bootstrapper stories when nothing new), summarizes relevant posts into Russian via the Gemini API, and posts a digest to a Telegram channel — plus a one-off script to publish an initial "evergreen marketing wisdom" post before the cron starts.

**Architecture:** Six small, independently-testable modules (`state`, `feeds`, `fetch`, `llm`, `telegram`, `digest`) composed by a thin `main.py` orchestrator. State (which items were already posted) lives in `state.json`, committed back to the repo by the GitHub Actions job after each run. No database, no server.

**Tech Stack:** Python 3.11+, `feedparser` (RSS parsing), `requests` (HTTP to Gemini + Telegram), `pytest` (tests), GitHub Actions (cron + secrets), Google Gemini API (`gemini-2.5-flash`, free tier), Telegram Bot API.

## Global Constraints

- All user-facing digest text (summaries, takeaways) MUST be in Russian — copied verbatim from spec.
- No paid services anywhere in the pipeline (RSS, GitHub Actions, Gemini free tier, Telegram Bot API are all $0) — from spec.
- Secrets (`GEMINI_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`) live only in GitHub Actions Secrets / environment variables, never hardcoded — from spec.
- If nothing relevant is found anywhere (primary + fallback), the run sends nothing and exits cleanly — from spec.
- Cron schedule: 09:00, 15:00, 21:00 Europe/Kyiv (documented as approximate — GitHub Actions cron is UTC-only, no DST awareness) — from spec.

---

### Task 1: Project scaffolding and state module

**Files:**
- Create: `requirements.txt`
- Create: `src/__init__.py`
- Create: `src/state.py`
- Create: `tests/__init__.py`
- Test: `tests/test_state.py`

**Interfaces:**
- Produces: `load_state(path: str) -> dict` — returns `{"seen_ids": [...]}`, empty list if file doesn't exist
- Produces: `save_state(path: str, state: dict) -> None`
- Produces: `is_seen(state: dict, item_id: str) -> bool`
- Produces: `mark_seen(state: dict, item_id: str) -> None`

- [ ] **Step 1: Create the project skeleton**

```bash
mkdir -p src tests content scripts .github/workflows
touch src/__init__.py tests/__init__.py
```

- [ ] **Step 2: Write `requirements.txt`**

```
feedparser==6.0.11
requests==2.32.3
pytest==8.3.3
```

- [ ] **Step 3: Write the failing test for state module**

```python
# tests/test_state.py
import json
from src.state import load_state, save_state, is_seen, mark_seen


def test_load_state_missing_file_returns_empty(tmp_path):
    path = tmp_path / "state.json"
    state = load_state(str(path))
    assert state == {"seen_ids": []}


def test_save_and_load_roundtrip(tmp_path):
    path = tmp_path / "state.json"
    save_state(str(path), {"seen_ids": ["a", "b"]})
    assert load_state(str(path)) == {"seen_ids": ["a", "b"]}
    with open(path) as f:
        assert json.load(f) == {"seen_ids": ["a", "b"]}


def test_is_seen_true_and_false():
    state = {"seen_ids": ["x"]}
    assert is_seen(state, "x") is True
    assert is_seen(state, "y") is False


def test_mark_seen_adds_id_once():
    state = {"seen_ids": []}
    mark_seen(state, "x")
    mark_seen(state, "x")
    assert state["seen_ids"] == ["x"]
```

- [ ] **Step 4: Run test to verify it fails**

Run: `pytest tests/test_state.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.state'`

- [ ] **Step 5: Implement `src/state.py`**

```python
import json
import os


def load_state(path: str) -> dict:
    if not os.path.exists(path):
        return {"seen_ids": []}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(path: str, state: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def is_seen(state: dict, item_id: str) -> bool:
    return item_id in state["seen_ids"]


def mark_seen(state: dict, item_id: str) -> None:
    if item_id not in state["seen_ids"]:
        state["seen_ids"].append(item_id)
```

- [ ] **Step 6: Run test to verify it passes**

Run: `pytest tests/test_state.py -v`
Expected: 4 passed

- [ ] **Step 7: Commit**

```bash
git add requirements.txt src/__init__.py src/state.py tests/__init__.py tests/test_state.py
git commit -m "feat: add state persistence module"
```

---

### Task 2: Sources configuration (primary + fallback feeds)

**Files:**
- Create: `src/feeds.py`
- Test: `tests/test_feeds.py`

**Interfaces:**
- Produces: `PRIMARY_SOURCES: list[dict]` — each `{"name": str, "feed_url": str}`
- Produces: `FALLBACK_SOURCES: list[dict]` — same shape

This task requires live research: confirm the correct RSS URL for Kyle Poyar's
newsletter (moved from Substack to Beehiiv in Jan 2026) and find/validate 4-6
working RSS feeds for bootstrapped-SaaS-with-near-zero-marketing-budget
content (Indie Hackers, Starter Story, Failory, and solo/AI-builder blogs
such as Marc Lou, Tony Dinh, Damon Chen, Daniel Vassallo).

- [ ] **Step 1: Resolve Kyle Poyar's current feed URL**

Use WebSearch/WebFetch to find Growth Unhinged's current RSS feed (it moved
to Beehiiv — try `https://www.growthunhinged.com/feed.xml`, check the site's
`<head>` for a `<link rel="alternate" type="application/rss+xml">` tag, or
search "growthunhinged.com rss feed beehiiv"). Fetch the candidate URL and
confirm it returns valid RSS/Atom XML with recent entries.

- [ ] **Step 2: Find and validate fallback pool feeds**

For each candidate (Indie Hackers, Starter Story, Failory, Marc Lou, Tony
Dinh, Damon Chen, Daniel Vassallo), search for their RSS feed URL and fetch
it with WebFetch to confirm it's valid XML with recent entries. Drop any
candidate whose feed 404s or has been dead for 6+ months. Keep at least 4
working fallback sources.

- [ ] **Step 3: Write the failing test for source list shape**

```python
# tests/test_feeds.py
from src.feeds import PRIMARY_SOURCES, FALLBACK_SOURCES


def _assert_valid_source_list(sources, expected_min_len):
    assert len(sources) >= expected_min_len
    seen_urls = set()
    for entry in sources:
        assert set(entry.keys()) == {"name", "feed_url"}
        assert entry["name"].strip() != ""
        assert entry["feed_url"].startswith("https://")
        assert entry["feed_url"] not in seen_urls
        seen_urls.add(entry["feed_url"])


def test_primary_sources_has_seven_valid_entries():
    _assert_valid_source_list(PRIMARY_SOURCES, expected_min_len=7)


def test_fallback_sources_has_at_least_four_valid_entries():
    _assert_valid_source_list(FALLBACK_SOURCES, expected_min_len=4)
```

- [ ] **Step 4: Run test to verify it fails**

Run: `pytest tests/test_feeds.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.feeds'`

- [ ] **Step 5: Implement `src/feeds.py`**

Write the confirmed URLs from Steps 1-2 into the file. Use the six already-
verified URLs below as-is; fill in the Kyle Poyar URL and the fallback pool
with what you found in Steps 1-2:

```python
PRIMARY_SOURCES = [
    {"name": "Arvid Kahl", "feed_url": "https://thebootstrappedfounder.com/feed"},
    {"name": "Jason Lemkin", "feed_url": "https://www.saastr.com/feed/"},
    {"name": "Kyle Poyar", "feed_url": "<RESOLVED IN STEP 1>"},
    {"name": "Emily Kramer & Kathleen Estreich", "feed_url": "https://newsletter.mkt1.co/feed"},
    {"name": "Lenny Rachitsky", "feed_url": "https://www.lennysnewsletter.com/feed"},
    {"name": "Rand Fishkin", "feed_url": "https://sparktoro.com/blog/feed"},
    {"name": "Pieter Levels", "feed_url": "https://levels.io/rss/"},
]

FALLBACK_SOURCES = [
    # Filled in from Step 2 — at least 4 entries, e.g.:
    # {"name": "Indie Hackers", "feed_url": "..."},
    # {"name": "Starter Story", "feed_url": "..."},
    # {"name": "Failory", "feed_url": "..."},
    # {"name": "Marc Lou", "feed_url": "..."},
]
```

- [ ] **Step 6: Run test to verify it passes**

Run: `pytest tests/test_feeds.py -v`
Expected: 2 passed

- [ ] **Step 7: Commit**

```bash
git add src/feeds.py tests/test_feeds.py
git commit -m "feat: add validated primary and fallback RSS source lists"
```

---

### Task 3: Feed fetching module

**Files:**
- Create: `src/fetch.py`
- Test: `tests/test_fetch.py`

**Interfaces:**
- Consumes: source dicts shaped `{"name": str, "feed_url": str}` (from Task 2's `src.feeds`)
- Produces: `fetch_entries(feed_url: str, source_name: str) -> list[dict]` — each dict `{"id": str, "source": str, "title": str, "link": str, "content": str}`
- Produces: `fetch_all(sources: list[dict]) -> list[dict]` — aggregates `fetch_entries` over all sources, skipping (with a printed warning) any source that raises

- [ ] **Step 1: Write the failing test**

```python
# tests/test_fetch.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_fetch.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.fetch'`

- [ ] **Step 3: Implement `src/fetch.py`**

```python
import feedparser


def fetch_entries(feed_url: str, source_name: str) -> list[dict]:
    parsed = feedparser.parse(feed_url)
    entries = []
    for entry in parsed.entries:
        item_id = entry.get("id") or entry.get("link")
        entries.append({
            "id": item_id,
            "source": source_name,
            "title": entry.get("title", ""),
            "link": entry.get("link", ""),
            "content": entry.get("summary", ""),
        })
    return entries


def fetch_all(sources: list[dict]) -> list[dict]:
    all_entries = []
    for source in sources:
        try:
            all_entries.extend(fetch_entries(source["feed_url"], source["name"]))
        except Exception as exc:
            print(f"WARNING: failed to fetch {source['name']} ({source['feed_url']}): {exc}")
    return all_entries
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_fetch.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add src/fetch.py tests/test_fetch.py
git commit -m "feat: add RSS feed fetching module"
```

---

### Task 4: Gemini summarization + relevance filter

**Files:**
- Create: `src/llm.py`
- Test: `tests/test_llm.py`

**Interfaces:**
- Consumes: `title: str, content: str, source_name: str, api_key: str` (content/title come from `fetch.fetch_entries` items)
- Produces: `summarize_and_filter(title: str, content: str, source_name: str, api_key: str) -> dict | None` — returns `None` if not relevant, else `{"summary": str, "takeaway": str}` (both in Russian)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_llm.py
import json
from unittest.mock import patch, MagicMock
from src.llm import summarize_and_filter


def _mock_response(payload: dict):
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "candidates": [
            {"content": {"parts": [{"text": json.dumps(payload)}]}}
        ]
    }
    return mock_resp


def test_relevant_post_returns_summary_and_takeaway():
    payload = {
        "relevant": True,
        "summary": "Автор рассказывает, как вырастить SaaS без бюджета.",
        "takeaway": "Начните с построения в открытую (building in public).",
    }
    with patch("src.llm.requests.post", return_value=_mock_response(payload)):
        result = summarize_and_filter("Title", "Body", "Author", "fake-key")

    assert result == {
        "summary": "Автор рассказывает, как вырастить SaaS без бюджета.",
        "takeaway": "Начните с построения в открытую (building in public).",
    }


def test_irrelevant_post_returns_none():
    payload = {"relevant": False, "summary": "", "takeaway": ""}
    with patch("src.llm.requests.post", return_value=_mock_response(payload)):
        result = summarize_and_filter("Title", "Body about hiring a VP of Sales", "Author", "fake-key")

    assert result is None


def test_http_error_propagates():
    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = RuntimeError("HTTP 500")
    with patch("src.llm.requests.post", return_value=mock_resp):
        try:
            summarize_and_filter("Title", "Body", "Author", "fake-key")
            assert False, "expected RuntimeError"
        except RuntimeError:
            pass
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_llm.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.llm'`

- [ ] **Step 3: Implement `src/llm.py`**

```python
import json
import requests

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

PROMPT_TEMPLATE = """Ты — ассистент телеграм-канала о SaaS-маркетинге с минимальным бюджетом.

Автор поста: {source_name}
Заголовок: {title}
Текст поста:
{content}

Задача:
1. Оцени, релевантен ли этот пост теме "маркетинг SaaS-продуктов с минимальным или нулевым бюджетом" (рост, привлечение пользователей, retention, позиционирование, дистрибуция, GTM, продуктовый маркетинг). Пост НЕ релевантен, если он посвящён исключительно фандрайзингу, найму персонала, юридическим вопросам или не связан с маркетингом/ростом.
2. Если релевантен — напиши:
   - summary: краткое изложение сути поста на русском языке, 2-4 предложения
   - takeaway: один конкретный практический вывод, применимый при нулевом бюджете, на русском языке, 1-2 предложения

Ответь строго в формате JSON: {{"relevant": true/false, "summary": "...", "takeaway": "..."}}
Если not relevant, summary и takeaway оставь пустыми строками.
"""


def summarize_and_filter(title: str, content: str, source_name: str, api_key: str) -> dict | None:
    prompt = PROMPT_TEMPLATE.format(source_name=source_name, title=title, content=content)
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"response_mime_type": "application/json"},
    }
    response = requests.post(f"{GEMINI_URL}?key={api_key}", json=payload, timeout=30)
    response.raise_for_status()
    data = response.json()
    text = data["candidates"][0]["content"]["parts"][0]["text"]
    parsed = json.loads(text)

    if not parsed.get("relevant"):
        return None
    return {"summary": parsed["summary"], "takeaway": parsed["takeaway"]}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_llm.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add src/llm.py tests/test_llm.py
git commit -m "feat: add Gemini relevance filter and Russian summarizer"
```

---

### Task 5: Telegram delivery module

**Files:**
- Create: `src/telegram.py`
- Test: `tests/test_telegram.py`

**Interfaces:**
- Consumes: `bot_token: str, chat_id: str, text: str`
- Produces: `send_message(bot_token: str, chat_id: str, text: str) -> None` — raises `RuntimeError` on API failure; splits `text` into chunks of at most 4096 characters (Telegram's hard limit), sent as separate sequential calls

- [ ] **Step 1: Write the failing test**

```python
# tests/test_telegram.py
from unittest.mock import patch, MagicMock
from src.telegram import send_message, MAX_MESSAGE_LENGTH


def test_send_message_short_text_single_call():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"ok": True}
    with patch("src.telegram.requests.post", return_value=mock_resp) as mock_post:
        send_message("token123", "chat456", "hello world")

    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    assert args[0] == "https://api.telegram.org/bottoken123/sendMessage"
    assert kwargs["json"]["chat_id"] == "chat456"
    assert kwargs["json"]["text"] == "hello world"


def test_send_message_long_text_splits_into_chunks():
    long_text = "x" * 9000
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"ok": True}
    with patch("src.telegram.requests.post", return_value=mock_resp) as mock_post:
        send_message("token123", "chat456", long_text)

    assert mock_post.call_count == 3
    for call in mock_post.call_args_list:
        assert len(call.kwargs["json"]["text"]) <= MAX_MESSAGE_LENGTH


def test_send_message_api_error_raises():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"ok": False, "description": "bad chat id"}
    with patch("src.telegram.requests.post", return_value=mock_resp):
        try:
            send_message("token123", "chat456", "hello")
            assert False, "expected RuntimeError"
        except RuntimeError as exc:
            assert "bad chat id" in str(exc)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_telegram.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.telegram'`

- [ ] **Step 3: Implement `src/telegram.py`**

```python
import requests

MAX_MESSAGE_LENGTH = 4096


def _chunk_text(text: str, size: int) -> list[str]:
    return [text[i:i + size] for i in range(0, len(text), size)] or [""]


def send_message(bot_token: str, chat_id: str, text: str) -> None:
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    for chunk in _chunk_text(text, MAX_MESSAGE_LENGTH):
        response = requests.post(url, json={
            "chat_id": chat_id,
            "text": chunk,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        }, timeout=30)
        data = response.json()
        if not data.get("ok"):
            raise RuntimeError(f"Telegram API error: {data.get('description')}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_telegram.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add src/telegram.py tests/test_telegram.py
git commit -m "feat: add Telegram delivery module"
```

---

### Task 6: Digest message formatting

**Files:**
- Create: `src/digest.py`
- Test: `tests/test_digest.py`

**Interfaces:**
- Consumes: item dicts shaped `{"source": str, "title": str, "link": str, "summary": str, "takeaway": str}` (fields come from merging a `fetch` entry with an `llm.summarize_and_filter` result), plus an optional `is_fallback: bool`
- Produces: `format_item(item: dict) -> str`
- Produces: `build_digest_message(items: list[dict]) -> str`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_digest.py
from src.digest import format_item, build_digest_message

PRIMARY_ITEM = {
    "source": "Arvid Kahl",
    "title": "How I Grew Without Ads",
    "link": "https://example.com/post",
    "summary": "Автор рассказывает про рост без рекламы.",
    "takeaway": "Публикуйте прогресс открыто каждую неделю.",
    "is_fallback": False,
}

FALLBACK_ITEM = {
    "source": "Marc Lou",
    "title": "0 to $10k MRR with no budget",
    "link": "https://example.com/fallback-post",
    "summary": "История о том, как продукт вырос без единого доллара на маркетинг.",
    "takeaway": "Запускайтесь на Twitter/X органически, до того как тратить деньги.",
    "is_fallback": True,
}


def test_format_item_primary_source():
    text = format_item(PRIMARY_ITEM)
    assert "Arvid Kahl" in text
    assert "How I Grew Without Ads" in text
    assert "Автор рассказывает про рост без рекламы." in text
    assert "Публикуйте прогресс открыто каждую неделю." in text
    assert "https://example.com/post" in text
    assert "резервный источник" not in text


def test_format_item_fallback_source_marks_it():
    text = format_item(FALLBACK_ITEM)
    assert "резервный источник" in text


def test_build_digest_message_joins_multiple_items():
    message = build_digest_message([PRIMARY_ITEM, FALLBACK_ITEM])
    assert "Arvid Kahl" in message
    assert "Marc Lou" in message
    assert message.count("🔹") == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_digest.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.digest'`

- [ ] **Step 3: Implement `src/digest.py`**

```python
def format_item(item: dict) -> str:
    fallback_note = " (резервный источник)" if item.get("is_fallback") else ""
    return (
        f"🔹 {item['source']}{fallback_note} — {item['title']}\n\n"
        f"{item['summary']}\n\n"
        f"💡 Практический вывод: {item['takeaway']}\n\n"
        f"🔗 {item['link']}"
    )


def build_digest_message(items: list[dict]) -> str:
    return "\n\n---\n\n".join(format_item(item) for item in items)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_digest.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add src/digest.py tests/test_digest.py
git commit -m "feat: add digest message formatting"
```

---

### Task 7: Orchestration (main.py)

**Files:**
- Create: `src/main.py`
- Test: `tests/test_main.py`

**Interfaces:**
- Consumes: `state.load_state/save_state/is_seen/mark_seen`, `feeds.PRIMARY_SOURCES/FALLBACK_SOURCES`, `fetch.fetch_all`, `llm.summarize_and_filter`, `telegram.send_message`, `digest.build_digest_message`
- Produces: `run(state_path: str, primary_sources: list[dict], fallback_sources: list[dict], gemini_api_key: str, telegram_bot_token: str, telegram_chat_id: str) -> None`
- Produces: CLI entry point in `if __name__ == "__main__":` reading `STATE_PATH`, `GEMINI_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` from environment variables (`STATE_PATH` defaults to `state.json`)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_main.py
from unittest.mock import patch
from src.main import run

PRIMARY_SOURCES = [{"name": "Author A", "feed_url": "https://a.example/feed"}]
FALLBACK_SOURCES = [{"name": "Fallback A", "feed_url": "https://fb.example/feed"}]

PRIMARY_ENTRY = {"id": "p1", "source": "Author A", "title": "T1", "link": "https://a.example/1", "content": "C1"}
FALLBACK_ENTRY = {"id": "f1", "source": "Fallback A", "title": "T2", "link": "https://fb.example/1", "content": "C2"}

LLM_RESULT = {"summary": "S", "takeaway": "K"}


def test_run_sends_digest_when_primary_has_new_relevant_item(tmp_path):
    state_path = str(tmp_path / "state.json")
    with patch("src.main.fetch_all", side_effect=[[PRIMARY_ENTRY]]) as mock_fetch, \
         patch("src.main.summarize_and_filter", return_value=LLM_RESULT), \
         patch("src.main.send_message") as mock_send:
        run(state_path, PRIMARY_SOURCES, FALLBACK_SOURCES, "gk", "tt", "cc")

    mock_fetch.assert_called_once_with(PRIMARY_SOURCES)
    mock_send.assert_called_once()
    sent_text = mock_send.call_args[0][2]
    assert "Author A" in sent_text

    from src.state import load_state, is_seen
    assert is_seen(load_state(state_path), "p1")


def test_run_falls_back_when_primary_has_nothing_relevant(tmp_path):
    state_path = str(tmp_path / "state.json")
    with patch("src.main.fetch_all", side_effect=[[PRIMARY_ENTRY], [FALLBACK_ENTRY]]), \
         patch("src.main.summarize_and_filter", side_effect=[None, LLM_RESULT]), \
         patch("src.main.send_message") as mock_send:
        run(state_path, PRIMARY_SOURCES, FALLBACK_SOURCES, "gk", "tt", "cc")

    mock_send.assert_called_once()
    sent_text = mock_send.call_args[0][2]
    assert "Fallback A" in sent_text
    assert "резервный источник" in sent_text


def test_run_sends_nothing_when_all_sources_empty(tmp_path):
    state_path = str(tmp_path / "state.json")
    with patch("src.main.fetch_all", side_effect=[[], []]), \
         patch("src.main.summarize_and_filter") as mock_llm, \
         patch("src.main.send_message") as mock_send:
        run(state_path, PRIMARY_SOURCES, FALLBACK_SOURCES, "gk", "tt", "cc")

    mock_llm.assert_not_called()
    mock_send.assert_not_called()


def test_run_skips_already_seen_items(tmp_path):
    state_path = str(tmp_path / "state.json")
    from src.state import load_state, save_state, mark_seen
    state = load_state(state_path)
    mark_seen(state, "p1")
    save_state(state_path, state)

    with patch("src.main.fetch_all", side_effect=[[PRIMARY_ENTRY], []]), \
         patch("src.main.summarize_and_filter") as mock_llm, \
         patch("src.main.send_message") as mock_send:
        run(state_path, PRIMARY_SOURCES, FALLBACK_SOURCES, "gk", "tt", "cc")

    mock_llm.assert_not_called()
    mock_send.assert_not_called()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_main.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.main'`

- [ ] **Step 3: Implement `src/main.py`**

```python
import os

from src.state import load_state, save_state, is_seen, mark_seen
from src.feeds import PRIMARY_SOURCES, FALLBACK_SOURCES
from src.fetch import fetch_all
from src.llm import summarize_and_filter
from src.telegram import send_message
from src.digest import build_digest_message


def run(state_path, primary_sources, fallback_sources, gemini_api_key, telegram_bot_token, telegram_chat_id):
    state = load_state(state_path)
    digest_items = []

    primary_entries = [e for e in fetch_all(primary_sources) if not is_seen(state, e["id"])]
    for entry in primary_entries:
        result = summarize_and_filter(entry["title"], entry["content"], entry["source"], gemini_api_key)
        mark_seen(state, entry["id"])
        if result:
            digest_items.append({**entry, **result, "is_fallback": False})

    if not digest_items:
        fallback_entries = [e for e in fetch_all(fallback_sources) if not is_seen(state, e["id"])]
        for entry in fallback_entries:
            result = summarize_and_filter(entry["title"], entry["content"], entry["source"], gemini_api_key)
            mark_seen(state, entry["id"])
            if result:
                digest_items.append({**entry, **result, "is_fallback": True})
                break

    if digest_items:
        message = build_digest_message(digest_items)
        send_message(telegram_bot_token, telegram_chat_id, message)

    save_state(state_path, state)


if __name__ == "__main__":
    run(
        state_path=os.environ.get("STATE_PATH", "state.json"),
        primary_sources=PRIMARY_SOURCES,
        fallback_sources=FALLBACK_SOURCES,
        gemini_api_key=os.environ["GEMINI_API_KEY"],
        telegram_bot_token=os.environ["TELEGRAM_BOT_TOKEN"],
        telegram_chat_id=os.environ["TELEGRAM_CHAT_ID"],
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_main.py -v`
Expected: 4 passed

- [ ] **Step 5: Run the full test suite**

Run: `pytest -v`
Expected: all tests across every module pass

- [ ] **Step 6: Commit**

```bash
git add src/main.py tests/test_main.py
git commit -m "feat: add orchestration entry point tying all modules together"
```

---

### Task 8: GitHub Actions workflow, state seed file, and README

**Files:**
- Create: `state.json`
- Create: `.github/workflows/digest.yml`
- Create: `README.md`
- Create: `.gitignore`

- [ ] **Step 1: Seed the initial state file**

```bash
echo '{"seen_ids": []}' > state.json
```

- [ ] **Step 2: Write `.gitignore`**

```
__pycache__/
*.pyc
.pytest_cache/
venv/
.env
```

- [ ] **Step 3: Write the GitHub Actions workflow**

```yaml
# .github/workflows/digest.yml
name: SaaS Marketing Digest

on:
  schedule:
    - cron: "0 6,12,18 * * *"
  workflow_dispatch: {}

permissions:
  contents: write

jobs:
  digest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run digest
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
        run: python -m src.main

      - name: Commit updated state
        run: |
          git config user.name "digest-bot"
          git config user.email "digest-bot@users.noreply.github.com"
          git add state.json
          git diff --staged --quiet || git commit -m "chore: update seen-items state"
          git push
```

- [ ] **Step 4: Write `README.md`**

```markdown
# SaaS Marketing Digest Bot

Публикует в Telegram-канал дайджест новых постов по SaaS-маркетингу с
минимальным бюджетом от 7 отобранных авторов, на русском языке, 3 раза в
день (09:00, 15:00, 21:00 по Киеву — см. примечание про DST ниже). Если
свежих постов у основных авторов нет, берёт историю из резервного пула
бутстрап-фаундеров.

## Настройка

1. **Telegram-бот**: создайте через [@BotFather](https://t.me/BotFather),
   сохраните токен.
2. **Telegram-канал**: создайте канал, добавьте бота администратором.
   Получите `chat_id` (для публичного канала это `@username_канала`; для
   приватного — числовой ID, который можно получить через
   `https://api.telegram.org/bot<TOKEN>/getUpdates` после отправки любого
   сообщения в канал).
3. **Gemini API-ключ**: получите бесплатно на
   [aistudio.google.com](https://aistudio.google.com).
4. **GitHub Secrets**: в настройках репозитория (Settings → Secrets and
   variables → Actions) добавьте:
   - `GEMINI_API_KEY`
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
5. Workflow `.github/workflows/digest.yml` запускается автоматически по
   расписанию, либо вручную через вкладку Actions → "SaaS Marketing
   Digest" → "Run workflow".

## Локальный запуск

```bash
pip install -r requirements.txt
export GEMINI_API_KEY=...
export TELEGRAM_BOT_TOKEN=...
export TELEGRAM_CHAT_ID=...
python -m src.main
```

## Тесты

```bash
pip install -r requirements.txt
pytest -v
```

## Примечание про расписание

GitHub Actions cron работает только в UTC и не учитывает переход на
летнее/зимнее время. Текущее расписание (`0 6,12,18 * * *`) соответствует
09:00/15:00/21:00 по Киеву в летний период (EEST, UTC+3); зимой (EET,
UTC+2) время сдвинется на час раньше. При необходимости поправьте cron
вручную дважды в год.
```

- [ ] **Step 5: Verify the full test suite still passes**

Run: `pytest -v`
Expected: all tests pass (this step touches no Python code, but confirms
nothing was broken by the scaffolding files)

- [ ] **Step 6: Commit**

```bash
git add state.json .github/workflows/digest.yml README.md .gitignore
git commit -m "chore: add GitHub Actions workflow, seed state, and README"
```

---

### Task 9: Initial "evergreen wisdom" post

**Files:**
- Create: `content/evergreen_post.md`
- Create: `scripts/send_evergreen.py`
- Test: `tests/test_send_evergreen.py`

**Interfaces:**
- Consumes: `telegram.send_message`
- Produces: `load_evergreen_text(path: str) -> str` in `scripts/send_evergreen.py`

This is the one-time research post described in the spec: timeless SaaS
marketing principles drawn from the archives of the same 7 authors —
positioning through niche, building in public, organic content marketing,
PLG mechanics, product-driven word-of-mouth, etc. — written in Russian with
attribution.

- [ ] **Step 1: Research and write the evergreen content**

Use WebFetch/WebSearch to review older posts (not just the latest RSS
items) from the 7 authors in `src/feeds.py` — their blog archives, "best
of" pages, and any well-known evergreen essays. Identify principles that
are explicitly framed by the author as durable/timeless, or that have
demonstrably held true across years of their writing. Write the result to
`content/evergreen_post.md` as the literal text to be sent to Telegram:
Russian language, structured as a short intro plus a numbered list of
principles, each with a one-line attribution to the author it came from,
formatted with Telegram-compatible HTML tags (`<b>`, `<i>`) rather than
Markdown syntax (Telegram's HTML parse mode is what `src/telegram.py`
uses).

- [ ] **Step 2: Write the failing test**

```python
# tests/test_send_evergreen.py
from unittest.mock import patch
from scripts.send_evergreen import load_evergreen_text, main


def test_load_evergreen_text_reads_file(tmp_path):
    path = tmp_path / "post.md"
    path.write_text("Привет, мир", encoding="utf-8")
    assert load_evergreen_text(str(path)) == "Привет, мир"


def test_main_sends_loaded_text_via_telegram(tmp_path):
    path = tmp_path / "post.md"
    path.write_text("Текст поста", encoding="utf-8")
    with patch("scripts.send_evergreen.send_message") as mock_send:
        main(str(path), "token123", "chat456")
    mock_send.assert_called_once_with("token123", "chat456", "Текст поста")
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/test_send_evergreen.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.send_evergreen'`

- [ ] **Step 4: Implement `scripts/send_evergreen.py`**

```python
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.telegram import send_message


def load_evergreen_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def main(path: str, bot_token: str, chat_id: str) -> None:
    text = load_evergreen_text(path)
    send_message(bot_token, chat_id, text)


if __name__ == "__main__":
    main(
        path=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "content", "evergreen_post.md"),
        bot_token=os.environ["TELEGRAM_BOT_TOKEN"],
        chat_id=os.environ["TELEGRAM_CHAT_ID"],
    )
```

Also create `scripts/__init__.py` (empty file) so `scripts.send_evergreen`
is importable in tests:

```bash
touch scripts/__init__.py
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_send_evergreen.py -v`
Expected: 2 passed

- [ ] **Step 6: Commit the script and content (do NOT run it yet)**

```bash
git add content/evergreen_post.md scripts/__init__.py scripts/send_evergreen.py tests/test_send_evergreen.py
git commit -m "feat: add evergreen wisdom post content and one-off sender script"
```

- [ ] **Step 7: Manual step — get explicit go-ahead before sending**

Do not run `python scripts/send_evergreen.py` automatically. Show the
rendered content of `content/evergreen_post.md` to the user, get explicit
confirmation, and only then run it manually (with `TELEGRAM_BOT_TOKEN` and
`TELEGRAM_CHAT_ID` set) to publish the first message to the channel. Only
after this confirmed send should the GitHub Actions cron (Task 8) be
enabled/merged to `main`.

---

## Post-plan verification

After all 9 tasks are complete:

- [ ] Run `pytest -v` — every test across all modules passes
- [ ] Run `python -m src.main` locally once with real secrets (or
      `workflow_dispatch` the Action manually) and confirm a message
      arrives in the Telegram channel, or that it exits cleanly with no
      message when there's nothing new
- [ ] Confirm `state.json` was updated after the run and the same items
      aren't re-sent on a second run
