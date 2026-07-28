from unittest.mock import patch, MagicMock
from src.telegram import send_message, MAX_MESSAGE_LENGTH


def test_send_message_short_text_single_call():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"ok": True}
    with patch("src.telegram.requests.post", return_value=mock_resp) as mock_post:
        send_message("token123", "chat456", "hello world")

    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    assert args[0] == "https://api.telegram.org/bottoken123/sendMessage"
    assert kwargs["json"]["chat_id"] == "chat456"
    assert kwargs["json"]["text"] == "hello world"


def test_send_message_long_text_splits_into_chunks():
    long_text = "x" * 9000
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"ok": True}
    with patch("src.telegram.requests.post", return_value=mock_resp) as mock_post:
        send_message("token123", "chat456", long_text)

    assert mock_post.call_count == 3
    for call in mock_post.call_args_list:
        assert len(call.kwargs["json"]["text"]) <= MAX_MESSAGE_LENGTH


def test_send_message_api_error_raises():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"ok": False, "description": "bad chat id"}
    with patch("src.telegram.requests.post", return_value=mock_resp):
        try:
            send_message("token123", "chat456", "hello")
            assert False, "expected RuntimeError"
        except RuntimeError as exc:
            assert "bad chat id" in str(exc)
