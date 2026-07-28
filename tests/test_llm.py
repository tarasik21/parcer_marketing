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
