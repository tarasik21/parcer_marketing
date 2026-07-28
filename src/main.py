import os

from src.state import load_state, save_state, is_seen, mark_seen
from src.feeds import PRIMARY_SOURCES, FALLBACK_SOURCES
from src.fetch import fetch_all
from src.llm import summarize_and_filter
from src.telegram import send_message
from src.digest import build_digest_message


def run(state_path, primary_sources, fallback_sources, gemini_api_key, telegram_bot_token, telegram_chat_id):
    state = load_state(state_path)
    try:
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
