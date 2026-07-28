import json
from src.state import load_state, save_state, is_seen, mark_seen


def test_load_state_missing_file_returns_empty(tmp_path):
    path = tmp_path / "state.json"
    state = load_state(str(path))
    assert state == {"seen_ids": []}


def test_save_and_load_roundtrip(tmp_path):
    path = tmp_path / "state.json"
    save_state(str(path), {"seen_ids": ["a", "b"]})
    assert load_state(str(path)) == {"seen_ids": ["a", "b"]}
    with open(path) as f:
        assert json.load(f) == {"seen_ids": ["a", "b"]}


def test_is_seen_true_and_false():
    state = {"seen_ids": ["x"]}
    assert is_seen(state, "x") is True
    assert is_seen(state, "y") is False


def test_mark_seen_adds_id_once():
    state = {"seen_ids": []}
    mark_seen(state, "x")
    mark_seen(state, "x")
    assert state["seen_ids"] == ["x"]
