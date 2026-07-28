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


def test_build_digest_message_joins_multiple_items():
    message = build_digest_message([PRIMARY_ITEM, FALLBACK_ITEM])
    assert "Arvid Kahl" in message
    assert "Marc Lou" in message
    assert message.count("🔹") == 2
