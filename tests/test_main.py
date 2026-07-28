from unittest.mock import patch
from src.main import run, MAX_ITEMS_PER_RUN

PRIMARY_SOURCES = [{"name": "Author A", "feed_url": "https://a.example/feed"}]
FALLBACK_SOURCES = [{"name": "Fallback A", "feed_url": "https://fb.example/feed"}]

PRIMARY_ENTRY = {"id": "p1", "source": "Author A", "title": "T1", "link": "https://a.example/1", "content": "C1"}
PRIMARY_ENTRY_2 = {"id": "p2", "source": "Author A", "title": "T3", "link": "https://a.example/2", "content": "C3"}
PRIMARY_ENTRY_3 = {"id": "p3", "source": "Author A", "title": "T4", "link": "https://a.example/3", "content": "C4"}
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


def test_run_continues_after_llm_failure_and_leaves_that_item_unseen(tmp_path):
    """A single bad Gemini response must not abort the run or mark that item seen."""
    state_path = str(tmp_path / "state.json")
    with patch("src.main.fetch_all", side_effect=[[PRIMARY_ENTRY, PRIMARY_ENTRY_2, PRIMARY_ENTRY_3]]), \
         patch("src.main.summarize_and_filter", side_effect=[None, RuntimeError("boom"), LLM_RESULT]) as mock_llm, \
         patch("src.main.send_message") as mock_send:
        run(state_path, PRIMARY_SOURCES, FALLBACK_SOURCES, "gk", "tt", "cc")

    # The loop kept going after the failure: all three entries were evaluated
    assert mock_llm.call_count == 3
    # The third (relevant) entry still produced a digest
    mock_send.assert_called_once()
    assert "T4" in mock_send.call_args[0][2]

    from src.state import load_state, is_seen
    state = load_state(state_path)
    assert is_seen(state, "p1")        # irrelevant → correctly excluded forever
    assert not is_seen(state, "p2")    # LLM failed → retried next run
    assert is_seen(state, "p3")        # relevant and delivered


def test_run_leaves_delivered_items_unseen_when_send_fails(tmp_path):
    """Delivery failure must not burn the digest items, but state so far is saved."""
    state_path = str(tmp_path / "state.json")
    with patch("src.main.fetch_all", side_effect=[[PRIMARY_ENTRY, PRIMARY_ENTRY_2]]), \
         patch("src.main.summarize_and_filter", side_effect=[None, LLM_RESULT]), \
         patch("src.main.send_message", side_effect=RuntimeError("telegram 400")):
        try:
            run(state_path, PRIMARY_SOURCES, FALLBACK_SOURCES, "gk", "tt", "cc")
            assert False, "expected run() to propagate the send failure"
        except RuntimeError:
            pass

    from src.state import load_state, is_seen
    state = load_state(state_path)
    assert is_seen(state, "p1")        # irrelevant item's progress persisted via finally
    assert not is_seen(state, "p2")    # relevant but undelivered → retried next run


def test_run_caps_number_of_llm_calls_per_run(tmp_path):
    """Cold-start backlogs must not fire an unbounded number of Gemini calls."""
    state_path = str(tmp_path / "state.json")
    backlog = [
        {"id": f"b{i}", "source": "Author A", "title": f"T{i}", "link": f"https://a.example/{i}", "content": "C"}
        for i in range(30)
    ]
    with patch("src.main.fetch_all", side_effect=[backlog]), \
         patch("src.main.summarize_and_filter", return_value=LLM_RESULT) as mock_llm, \
         patch("src.main.send_message"):
        run(state_path, PRIMARY_SOURCES, FALLBACK_SOURCES, "gk", "tt", "cc")

    assert mock_llm.call_count == MAX_ITEMS_PER_RUN

    from src.state import load_state, is_seen
    state = load_state(state_path)
    assert is_seen(state, f"b{MAX_ITEMS_PER_RUN - 1}")
    assert not is_seen(state, f"b{MAX_ITEMS_PER_RUN}")  # rest drains on later runs


def test_run_caps_fallback_entries_evaluated_per_run(tmp_path):
    state_path = str(tmp_path / "state.json")
    backlog = [
        {"id": f"fb{i}", "source": "Fallback A", "title": f"T{i}", "link": f"https://fb.example/{i}", "content": "C"}
        for i in range(30)
    ]
    with patch("src.main.fetch_all", side_effect=[[], backlog]), \
         patch("src.main.summarize_and_filter", return_value=None) as mock_llm, \
         patch("src.main.send_message") as mock_send:
        run(state_path, PRIMARY_SOURCES, FALLBACK_SOURCES, "gk", "tt", "cc")

    assert mock_llm.call_count == MAX_ITEMS_PER_RUN
    mock_send.assert_not_called()
