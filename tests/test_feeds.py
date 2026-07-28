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
