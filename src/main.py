import os

from src.state import load_state, save_state, is_seen, mark_seen
from src.feeds import PRIMARY_SOURCES, FALLBACK_SOURCES
from src.fetch import fetch_all
from src.llm import summarize_and_filter
from src.telegram import send_message
from src.digest import build_digest_message

# Upper bound on how many unseen entries are sent to Gemini in a single run.
# Protects the free-tier per-minute rate limit on a cold start / large backlog:
# state.json persists between runs, so a backlog simply drains this many items
# per cron invocation until it catches up with the feeds.
MAX_ITEMS_PER_RUN = 10


def run(state_path, primary_sources, fallback_sources, gemini_api_key, telegram_bot_token, telegram_chat_id):
    state = load_state(state_path)
    try:
        digest_items = []

        primary_entries = [e for e in fetch_all(primary_sources) if not is_seen(state, e["id"])]
        for entry in primary_entries[:MAX_ITEMS_PER_RUN]:
            try:
                result = summarize_and_filter(entry["title"], entry["content"], entry["source"], gemini_api_key)
            except Exception as exc:
                # Transient failures (rate limit, network blip, malformed response)
                # must not abort the run and must not mark the entry seen — it is
                # retried on the next run.
                print(f"WARNING: failed to summarize entry {entry['id']} from {entry['source']}: {exc}")
                continue
            if result:
                # Marked seen only after the digest is successfully delivered.
                digest_items.append({**entry, **result, "is_fallback": False})
            else:
                mark_seen(state, entry["id"])

        if not digest_items:
            fallback_entries = [e for e in fetch_all(fallback_sources) if not is_seen(state, e["id"])]
            for entry in fallback_entries[:MAX_ITEMS_PER_RUN]:
                try:
                    result = summarize_and_filter(entry["title"], entry["content"], entry["source"], gemini_api_key)
                except Exception as exc:
                    print(f"WARNING: failed to summarize entry {entry['id']} from {entry['source']}: {exc}")
                    continue
                if result:
                    digest_items.append({**entry, **result, "is_fallback": True})
                    break
                mark_seen(state, entry["id"])

        if digest_items:
            message = build_digest_message(digest_items)
            send_message(telegram_bot_token, telegram_chat_id, message)
            # Only after a successful send: if send_message raised, these items
            # stay unseen and are retried on the next run.
            for item in digest_items:
                mark_seen(state, item["id"])
    finally:
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
