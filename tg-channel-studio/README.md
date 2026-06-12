# TG Channel Studio

Multi-tenant SaaS для генерации и управления Telegram-каналами: подключаешь каналы-доноры → система забирает их посты через userbot → рерайтит через Claude под профиль твоего канала → публикует по расписанию через Bot API. Монетизация — usage-based кредиты (Stripe). Публичный SEO-лендинг и блог — в `marketing/`.

## Архитектура

```
marketing/ (Next.js, SEO-лендинг+блог)        frontend/ (Next.js дашборд)
                                                     │ JWT
                                              Backend (FastAPI, multi-tenant)──► PostgreSQL
                                                     │                            ▲   Redis
        ┌────────────────┬───────────────────────────┤
  ingest worker     generator worker            publisher worker
  (Telethon,        (Claude рерайт,             (Bot API, медиа,
   DonorSource,      фанаут по орг,              расписание, ретраи,
   медиа, дедуп)     кредит-гейтинг)             алерты)
                          │
                     Stripe (кредиты) ◄── webhook ── billing API
```

**Тенантность:** `User` ↔ `Membership` ↔ `Organization`. Все ресурсы (`Channel`, `Post`, `DonorSubscription`, `Alert`, `CreditLedger`) scoped по `org_id`. Каналы-доноры расшарены: `DonorSource` скрапится один раз на всех, `DonorSubscription` — подписка организации со своими фильтрами и каналами-получателями (меньше нагрузки на Telegram).

**Монетизация:** баланс кредитов на организацию, `CreditLedger` — полный аудит. 1 пост дебетует `ceil(cost_usd * markup / credit_price)` кредитов. Пакеты покупаются через Stripe Checkout, вебхук идемпотентно пополняет баланс. При нуле баланса генерация останавливается и поднимается алерт. Реферальная программа: +300 кредитов обоим.

## Пайплайн поста

```
DonorSource ──ingest──► raw_post(fanned_out=false) ──generator──► фанаут по подпискам
                                                                       │ кредит-гейтинг + дебет
                                                                       ▼
                          post(review | scheduled) ──publisher──► published | failed
```

- **Уровень рерайта** на канал: 1 лёгкий, 2 глубокий, 3 «по мотивам».
- **Анти-плагиат**: рерайт отклоняется при похожести > `MAX_REWRITE_SIMILARITY`.
- **Перенос медиа**: ingest скачивает фото донора, publisher отправляет через `sendPhoto`.
- **Слоты публикации**: `posts_per_day` распределяются по нерабочим часам с учётом таймзоны.

## Быстрый старт

```bash
cp .env.example .env       # SECRET_KEY, ANTHROPIC_API_KEY, STRIPE_*, TELEGRAM_API_ID/HASH
docker compose up --build
```

- Дашборд: http://localhost:3000 → `/signup`
- Лендинг: http://localhost:3001
- API: http://localhost:8000/docs

### Первый запуск userbot (одноразово)

```bash
docker compose run --rm worker-ingest python -c "
from telethon.sync import TelegramClient
from app.config import get_settings
s = get_settings()
TelegramClient(s.telethon_session, s.telegram_api_id, s.telegram_api_hash).start()
print('session saved')"
```

### Stripe

1. Создай продукты-пакеты кредитов, скопируй их Price ID.
2. Заполни `STRIPE_PRICE_CREDITS` как JSON `{"price_xxx": 5000, ...}` в `.env`.
3. Настрой вебхук на `POST /api/billing/webhook`, событие `checkout.session.completed`, секрет → `STRIPE_WEBHOOK_SECRET`.

## Разработка без Docker

```bash
cd backend
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload
python -m app.workers.ingest      # отдельные терминалы
python -m app.workers.generator
python -m app.workers.publisher
pytest -q                          # тесты (изоляция org, кредиты, Stripe webhook)

cd ../frontend && npm install && npm run dev        # дашборд :3000
cd ../marketing && npm install && npm run dev        # лендинг :3001
```

## Тесты и CI

`backend/tests/` (pytest + aiosqlite): изоляция организаций, приветственные/реферальные кредиты, дебет и гейтинг, идемпотентность Stripe-вебхука, фильтры/дедуп, расписание. CI (`.github/workflows/ci.yml`): ruff + pytest + сборка обоих фронтов.

## ⚠️ Важные оговорки

- **Userbot-скрапинг** — серая зона ToS Telegram. Отдельный «прогретый» аккаунт, встроенные интервалы и джиттер; риск ограничений остаётся.
- **Авторские права**: рерайт чужого контента — юридический риск; анти-плагиат гейт снижает, но не устраняет его.
- Перед продом: смени `SECRET_KEY`, задай `CORS_ORIGINS`, закрой порты 8000/5432 за reverse-proxy, подключи `SENTRY_DSN`.

## Документы
- [ROADMAP.md](ROADMAP.md) — список фич и статусы.
- [MARKETING.md](MARKETING.md) — стратегия продвижения, SEO-кластеры, воронка, метрики.

## Перенос в отдельный репозиторий

Проект самодостаточен (`backend/`, `frontend/`, `marketing/`, `docker-compose.yml`, CI). Создай пустой репо `tg-channel-studio` и:

```bash
git clone --no-checkout https://github.com/AlexKorbut/product-launcher tmp
cd tmp && git checkout claude/telegram-dashboard-plan-1ajng6 -- tg-channel-studio
cd tg-channel-studio && git init && git add -A && git commit -m "Initial: TG Channel Studio"
git remote add origin git@github.com:AlexKorbut/tg-channel-studio.git
git push -u origin main
```
