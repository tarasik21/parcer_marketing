import feedparser


def fetch_entries(feed_url: str, source_name: str) -> list[dict]:
    parsed = feedparser.parse(feed_url)
    # feedparser does not raise on a dead URL, 404 or garbage payload — it
    # returns normally with bozo=True and (usually) no entries. Surface that as
    # a warning instead of letting a permanently dead feed look like "no news".
    if parsed.get("bozo"):
        print(f"WARNING: feed for {source_name} ({feed_url}) appears malformed or unreachable (bozo)")
    entries = []
    for entry in parsed.entries:
        item_id = entry.get("id") or entry.get("link")
        entries.append({
            "id": item_id,
            "source": source_name,
            "title": entry.get("title", ""),
            "link": entry.get("link", ""),
            "content": entry.get("summary", ""),
        })
    return entries


def fetch_all(sources: list[dict]) -> list[dict]:
    all_entries = []
    for source in sources:
        try:
            all_entries.extend(fetch_entries(source["feed_url"], source["name"]))
        except Exception as exc:
            print(f"WARNING: failed to fetch {source['name']} ({source['feed_url']}): {exc}")
    return all_entries
