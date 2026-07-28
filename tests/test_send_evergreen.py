from unittest.mock import patch
from scripts.send_evergreen import load_evergreen_text, main


def test_load_evergreen_text_reads_file(tmp_path):
    path = tmp_path / "post.md"
    path.write_text("Привет, мир", encoding="utf-8")
    assert load_evergreen_text(str(path)) == "Привет, мир"


def test_main_sends_loaded_text_via_telegram(tmp_path):
    path = tmp_path / "post.md"
    path.write_text("Текст поста", encoding="utf-8")
    with patch("scripts.send_evergreen.send_message") as mock_send:
        main(str(path), "token123", "chat456")
    mock_send.assert_called_once_with("token123", "chat456", "Текст поста")
