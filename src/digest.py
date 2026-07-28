import html


def format_item(item: dict) -> str:
    # Telegram is called with parse_mode="HTML", so every dynamic field (RSS
    # titles, Gemini-generated text, source names, links) must be escaped.
    # The emoji/labels below are our own static text and stay unescaped.
    # quote=False: Telegram only requires <, > and & to be escaped in text
    # content; escaping quotes/apostrophes risks rendering literal &quot;/&#x27;.
    fallback_note = " (резервный источник)" if item.get("is_fallback") else ""
    source = html.escape(item["source"], quote=False)
    title = html.escape(item["title"], quote=False)
    summary = html.escape(item["summary"], quote=False)
    takeaway = html.escape(item["takeaway"], quote=False)
    link = html.escape(item["link"], quote=False)
    return (
        f"🔹 {source}{fallback_note} — {title}\n\n"
        f"{summary}\n\n"
        f"💡 Практический вывод: {takeaway}\n\n"
        f"🔗 {link}"
    )


def build_digest_message(items: list[dict]) -> str:
    return "\n\n---\n\n".join(format_item(item) for item in items)
