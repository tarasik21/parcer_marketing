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
