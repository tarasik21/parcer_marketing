# SaaS Marketing Digest Bot

Публикует в Telegram-канал дайджест новых постов по SaaS-маркетингу с
минимальным бюджетом от 7 отобранных авторов, на русском языке, 3 раза в
день (09:00, 15:00, 21:00 по Киеву — см. примечание про DST ниже). Если
свежих постов у основных авторов нет, берёт историю из резервного пула
бутстрап-фаундеров.

## Настройка

1. **Telegram-бот**: создайте через [@BotFather](https://t.me/BotFather),
   сохраните токен.
2. **Telegram-канал**: создайте канал, добавьте бота администратором.
   Получите `chat_id` (для публичного канала это `@username_канала`; для
   приватного — числовой ID, который можно получить через
   `https://api.telegram.org/bot<TOKEN>/getUpdates` после отправки любого
   сообщения в канал).
3. **Gemini API-ключ**: получите бесплатно на
   [aistudio.google.com](https://aistudio.google.com).
4. **GitHub Secrets**: в настройках репозитория (Settings → Secrets and
   variables → Actions) добавьте:
   - `GEMINI_API_KEY`
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
5. Workflow `.github/workflows/digest.yml` запускается автоматически по
   расписанию, либо вручную через вкладку Actions → "SaaS Marketing
   Digest" → "Run workflow".

## Локальный запуск

```bash
pip install -r requirements.txt
export GEMINI_API_KEY=...
export TELEGRAM_BOT_TOKEN=...
export TELEGRAM_CHAT_ID=...
python -m src.main
```

## Разовый вечнозелёный пост

Перед первым запуском канала нужно **один раз вручную** опубликовать
вечнозелёный пост (`content/evergreen_post.md`):

```bash
export TELEGRAM_BOT_TOKEN=...
export TELEGRAM_CHAT_ID=...
python scripts/send_evergreen.py
```

Это разовый шаг, выполняемый человеком **до включения** GitHub Actions
workflow (расписания/cron). Скрипт не входит в автоматический пайплайн и
не запускается workflow'ом — повторный запуск отправит пост ещё раз.

## Тесты

```bash
pip install -r requirements.txt
pytest -v
```

## Примечание про расписание

GitHub Actions cron работает только в UTC и не учитывает переход на
летнее/зимнее время. Текущее расписание (`0 6,12,18 * * *`) соответствует
09:00/15:00/21:00 по Киеву в летний период (EEST, UTC+3); зимой (EET,
UTC+2) время сдвинется на час раньше. При необходимости поправьте cron
вручную дважды в год.
