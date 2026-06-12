# TG Channel Studio

Дашборд для генерации и управления Telegram-каналами: подключаешь каналы-доноры → система забирает их посты через userbot → рерайтит через Claude под профиль твоего канала → публикует по расписанию через Bot API.

## Архитектура

```
Frontend (Next.js) ──► Backend (FastAPI, JWT) ──► PostgreSQL
                                                     ▲
        ┌────────────────────┬───────────────────────┤
        │                    │                       │
  ingest worker        generator worker        publisher worker
  (Telethon userbot,   (Anthropic API,         (Bot API, httpx,
   читает доноров,      рерайт + анти-          расписание, ретраи,
   дедуп + фильтры)     плагиат гейт)           flood-wait)
```

- **Очередь — на БД** (статусы постов + поллинг воркеров). Это осознанное упрощение MVP: меньше движущихся частей, чем Redis/Celery; миграция на Redis запланирована в v0.2 при росте нагрузки.
- Bot-токены каналов хранятся в БД **зашифрованными** (Fernet, ключ выводится из `SECRET_KEY`).

## Пайплайн поста

```
донор ──ingest──► raw_post(new) ──generator──► post(review | scheduled)
                                                  │ approve / auto_publish
                                                  ▼
                              post(scheduled) ──publisher──► published | failed
```

- **Уровень рерайта** (на канал): 1 — лёгкий, 2 — глубокий, 3 — «по мотивам».
- **Анти-плагиат**: рерайт отклоняется, если похожесть на оригинал > `MAX_REWRITE_SIMILARITY`.
- **Авто-публикация** — флаг на канал; при выключении посты попадают в очередь модерации.
- **Слоты публикации**: `posts_per_day` равномерно распределяются по нерабочим («тихим») часам канала с учётом таймзоны.

## Быстрый старт

```bash
cp .env.example .env       # заполни SECRET_KEY, ANTHROPIC_API_KEY, TELEGRAM_API_ID/HASH, ADMIN_*
docker compose up --build
```

- UI: http://localhost:3000 (логин — `ADMIN_EMAIL` / `ADMIN_PASSWORD`)
- API: http://localhost:8000/docs

### Первый запуск userbot (одноразово)

Telethon-сессии нужна интерактивная авторизация по номеру телефона:

```bash
docker compose run --rm worker-ingest python -c "
from telethon.sync import TelegramClient
from app.config import get_settings
s = get_settings()
TelegramClient(s.telethon_session, s.telegram_api_id, s.telegram_api_hash).start()
print('session saved')"
```

После этого сессия сохраняется в volume `telethon` и воркер работает автономно.

### Настройка через UI

1. **Каналы** → добавь свой канал: @username, токен бота (бот должен быть админом канала — кнопка 🤖 проверяет права), тематика/тон/аудитория, уровень рерайта, постов в день.
2. **Доноры** → добавь @username публичных каналов-источников, привяжи к своим каналам, настрой фильтры (мин. длина, стоп-слова, пропуск рекламы).
3. **Очередь** → смотри сгенерированные посты, редактируй, аппрувь (если модерация включена) или жди авто-публикации.

## Разработка без Docker

```bash
cd backend
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload          # API
python -m app.workers.ingest           # отдельные терминалы
python -m app.workers.generator
python -m app.workers.publisher

cd ../frontend
npm install && npm run dev             # http://localhost:3000, API проксируется на :8000
```

## ⚠️ Важные оговорки

- **Userbot-скрапинг чужих каналов** — серая зона ToS Telegram. Используй отдельный «прогретый» аккаунт; интервалы опроса и джиттер уже встроены, но риск ограничений аккаунта остаётся.
- **Авторские права**: рерайт чужого контента — юридический риск; анти-плагиат гейт снижает, но не устраняет его.
- Перед продом смени `SECRET_KEY`, `ADMIN_PASSWORD` и закрой порты 8000/5432 за reverse-proxy.

## Перенос в отдельный репозиторий

Проект самодостаточен. Создай пустой репо `tg-channel-studio` на GitHub и:

```bash
git clone --no-checkout https://github.com/AlexKorbut/product-launcher tmp
cd tmp && git checkout claude/telegram-dashboard-plan-1ajng6 -- tg-channel-studio
cd tg-channel-studio
git init && git add -A && git commit -m "Initial commit: TG Channel Studio MVP"
git remote add origin git@github.com:AlexKorbut/tg-channel-studio.git
git push -u origin main
```

Роадмап и список фич: [ROADMAP.md](ROADMAP.md)
