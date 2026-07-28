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
    # Exact output match to catch regressions in formatting, field order, or whitespace
    assert text == (
        "🔹 Arvid Kahl — How I Grew Without Ads\n\n"
        "Автор рассказывает про рост без рекламы.\n\n"
        "💡 Практический вывод: Публикуйте прогресс открыто каждую неделю.\n\n"
        "🔗 https://example.com/post"
    )
    # Substring assertions as additional safeguard
    assert "Arvid Kahl" in text
    assert "How I Grew Without Ads" in text
    assert "Автор рассказывает про рост без рекламы." in text
    assert "Публикуйте прогресс открыто каждую неделю." in text
    assert "https://example.com/post" in text
    assert "резервный источник" not in text


def test_format_item_fallback_source_marks_it():
    text = format_item(FALLBACK_ITEM)
    # Exact output match to catch regressions in fallback marker placement and formatting
    assert text == (
        "🔹 Marc Lou (резервный источник) — 0 to $10k MRR with no budget\n\n"
        "История о том, как продукт вырос без единого доллара на маркетинг.\n\n"
        "💡 Практический вывод: Запускайтесь на Twitter/X органически, до того как тратить деньги.\n\n"
        "🔗 https://example.com/fallback-post"
    )
    # Substring assertion as additional safeguard
    assert "резервный источник" in text


HTML_UNSAFE_ITEM = {
    "source": "Emily Kramer & Kathleen Estreich",
    "title": "From <$1k MRR> to growth",
    "link": "https://example.com/post?a=1&b=2",
    "summary": "Рост с <$1k MRR & без бюджета.",
    "takeaway": "Пишите в открытую <every week> & измеряйте.",
    "is_fallback": False,
}


def test_format_item_escapes_html_special_characters():
    text = format_item(HTML_UNSAFE_ITEM)
    assert text == (
        "🔹 Emily Kramer &amp; Kathleen Estreich — From &lt;$1k MRR&gt; to growth\n\n"
        "Рост с &lt;$1k MRR &amp; без бюджета.\n\n"
        "💡 Практический вывод: Пишите в открытую &lt;every week&gt; &amp; измеряйте.\n\n"
        "🔗 https://example.com/post?a=1&amp;b=2"
    )
    # No unescaped markup characters survive from the dynamic fields
    assert "<" not in text
    assert ">" not in text
    assert "Kramer & Kathleen" not in text
    # Our own static formatting is untouched
    assert "🔹" in text and "💡" in text and "🔗" in text


def test_format_item_escapes_fallback_item_without_touching_marker():
    text = format_item({**HTML_UNSAFE_ITEM, "is_fallback": True})
    assert text.startswith("🔹 Emily Kramer &amp; Kathleen Estreich (резервный источник) — ")


def test_build_digest_message_joins_multiple_items():
    message = build_digest_message([PRIMARY_ITEM, FALLBACK_ITEM])
    assert "Arvid Kahl" in message
    assert "Marc Lou" in message
    assert message.count("🔹") == 2
