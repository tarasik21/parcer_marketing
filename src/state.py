import json
import os


def load_state(path: str) -> dict:
    if not os.path.exists(path):
        return {"seen_ids": []}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(path: str, state: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def is_seen(state: dict, item_id: str) -> bool:
    return item_id in state["seen_ids"]


def mark_seen(state: dict, item_id: str) -> None:
    if item_id not in state["seen_ids"]:
        state["seen_ids"].append(item_id)
