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
