import json
from typing import Optional
import requests

# "-latest" alias used deliberately: pinned versions (gemini-2.5-flash, gemini-2.0-flash, etc.)
# returned 404/zero-quota for newly created API keys as of 2026-07-28; the alias tracks
# whatever free-tier-eligible model Google currently points it to.
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent"

PROMPT_TEMPLATE = """Ты — ассистент телеграм-канала о SaaS-маркетинге с минимальным бюджетом.

Автор поста: {source_name}
Заголовок: {title}
Текст поста:
{content}

Задача:
1. Оцени, релевантен ли этот пост теме "маркетинг SaaS-продуктов с минимальным или нулевым бюджетом" (рост, привлечение пользователей, retention, позиционирование, дистрибуция, GTM, продуктовый маркетинг). Пост НЕ релевантен, если он посвящён исключительно фандрайзингу, найму персонала, юридическим вопросам или не связан с маркетингом/ростом.
2. Если релевантен — напиши:
   - summary: краткое изложение сути поста на русском языке, 2-4 предложения
   - takeaway: один конкретный практический вывод, применимый при нулевом бюджете, на русском языке, 1-2 предложения

Ответь строго в формате JSON: {{"relevant": true/false, "summary": "...", "takeaway": "..."}}
Если not relevant, summary и takeaway оставь пустыми строками.
"""


def summarize_and_filter(title: str, content: str, source_name: str, api_key: str) -> Optional[dict]:
    prompt = PROMPT_TEMPLATE.format(source_name=source_name, title=title, content=content)
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"response_mime_type": "application/json"},
    }
    response = requests.post(f"{GEMINI_URL}?key={api_key}", json=payload, timeout=30)
    response.raise_for_status()
    data = response.json()
    text = data["candidates"][0]["content"]["parts"][0]["text"]
    parsed = json.loads(text)

    if not parsed.get("relevant"):
        return None
    return {"summary": parsed["summary"], "takeaway": parsed["takeaway"]}
