# Деплой TG Channel Studio в прод

Пошаговый чеклист. Рекомендованный путь — один VPS + Docker Compose + Caddy (авто-TLS),
он совпадает с готовым `docker-compose.yml`. Managed-альтернативы — в конце.

---

## 0. Что понадобится
- Домен (напр. `tgchannelstudio.com`) и доступ к DNS.
- VPS: 2 vCPU / 4 GB RAM / 40 GB SSD — достаточно для старта (Hetzner/DO/Vultr).
- Ключи: Anthropic и/или OpenAI; Stripe (live); Telegram `api_id`/`api_hash` (my.telegram.org).
- Отдельный «прогретый» Telegram-аккаунт для userbot.

---

## 1. DNS
Заведи A-записи на IP сервера:

| Запись | Назначение |
|---|---|
| `tgchannelstudio.com` | маркетинг-лендинг |
| `www` | лендинг (Caddy редиректит) |
| `app.tgchannelstudio.com` | дашборд (внутри проксирует `/api/*` в backend) |

> Backend наружу **не публикуется** — Stripe и фронт ходят на него через `app.домен/api/...`.

---

## 2. Сервер
```bash
# Docker + compose plugin
curl -fsSL https://get.docker.com | sh
git clone <твой-репозиторий> tg-channel-studio && cd tg-channel-studio
cp .env.example .env
```

---

## 3. Заполни `.env` (прод-значения)
```ini
SECRET_KEY=<openssl rand -hex 32>            # ОБЯЗАТЕЛЬНО смени
POSTGRES_PASSWORD=<сильный пароль>
PUBLIC_BASE_URL=https://app.tgchannelstudio.com
CORS_ORIGINS=https://app.tgchannelstudio.com
SITE_URL=https://tgchannelstudio.com
APP_URL=https://app.tgchannelstudio.com

# LLM
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
# (опц.) OPENAI_API_KEY=...  OPENAI_BASE_URL=...

# Stripe (live)
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...              # из шага 6
STRIPE_PRICE_CREDITS={"price_live_5000":5000,"price_live_20000":20000}

# Telegram userbot
TELEGRAM_API_ID=...
TELEGRAM_API_HASH=...

# Email (для верификации/сброса/инвайтов)
SMTP_HOST=smtp.provider.com
SMTP_PORT=587
SMTP_USER=...
SMTP_PASSWORD=...
EMAIL_FROM=no-reply@tgchannelstudio.com

# (опц.) SENTRY_DSN=...
```
> Сгенерировать `SECRET_KEY`: `openssl rand -hex 32`.

Также впиши свои домены/почту в **`Caddyfile`**.

---

## 4. Запуск
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```
- Caddy сам получит TLS-сертификаты на оба домена.
- Backend на старте прогоняет `alembic upgrade head` (схема создаётся автоматически).
- Внутренние порты (8000/5432/6379) наружу не торчат — только 80/443 через Caddy.

Проверка:
```bash
curl -fsS https://app.tgchannelstudio.com/api/health   # {"status":"ok"}
curl -fsS https://app.tgchannelstudio.com/api/ready    # {"status":"ready"} — БД жива
```

---

## 5. Первая авторизация userbot (одноразово, интерактивно)
```bash
docker compose run --rm worker-ingest python -c "
from telethon.sync import TelegramClient
from app.config import get_settings
s = get_settings()
TelegramClient(s.telethon_session, s.telegram_api_id, s.telegram_api_hash).start()
print('session saved')"
```
Введи номер телефона и код. Сессия сохранится в volume `telethon`, дальше воркер работает сам.

---

## 6. Stripe (live)
1. Создай продукты-пакеты кредитов → скопируй их **Price ID** в `STRIPE_PRICE_CREDITS` (JSON `price→кредиты`).
2. Webhooks → Add endpoint:
   - URL: `https://app.tgchannelstudio.com/api/billing/webhook`
   - Событие: `checkout.session.completed`
   - Скопируй **Signing secret** → `STRIPE_WEBHOOK_SECRET`, перезапусти backend.
3. Тест: оформи покупку тестовой картой `4242 4242 4242 4242` (в test-mode) → баланс кредитов вырос, в `/billing` появилась запись `purchase`.

---

## 7. SEO / маркетинг
- **Search Console**: добавь оба домена, подтверди владение (DNS-TXT), отправь `https://tgchannelstudio.com/sitemap.xml`.
- Проверь `https://tgchannelstudio.com/robots.txt` и OG-теги (Open Graph debugger).
- Аналитика: подключи Plausible/GA на лендинг и дашборд (вставь скрипт в `layout.tsx`).
- Программные страницы `/use-cases/*` и 5 статей блога уже готовы — наращивай по `MARKETING.md`.

---

## 8. Безопасность (чеклист перед публичным запуском)
- [ ] `SECRET_KEY` и `POSTGRES_PASSWORD` уникальные, не из примера.
- [ ] `CORS_ORIGINS` = только домен дашборда (не `*`).
- [ ] Порты 8000/5432/6379 не опубликованы (прод-оверлей это обеспечивает).
- [ ] Файрвол сервера открыт только на 22/80/443.
- [ ] `.env` не в git (уже в `.gitignore`), бэкап секретов в менеджере.
- [ ] (опц.) `SENTRY_DSN` для алертов об ошибках.

---

## 9. Бэкапы и обновления
```bash
# Бэкап БД
docker compose exec db pg_dump -U studio studio | gzip > backup_$(date +%F).sql.gz

# Обновление кода
git pull && docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```
Тома `pgdata`, `telethon`, `media` переживают пересборку. Настрой регулярный `pg_dump` по cron.

---

## 10. Пост-деплой смоук
1. Регистрация на `app.домен` → пришло письмо верификации (или ссылка в логах при пустом SMTP).
2. Онбординг: канал (кнопка 🤖 подтверждает права бота) + донор.
3. `/raw` → «Переписать» → пост появился в `/queue`, кредиты списались.
4. Покупка кредитов (Stripe test) → баланс вырос.
5. Дождись слота публикации → пост ушёл в канал; в `/calendar` видно опубликованный.

---

## 11. Авто-деплой через GitHub Actions
Workflow `.github/workflows/deploy.yml`: на push в `main` прогоняет ruff+pytest, затем по SSH
заходит на сервер, делает `git pull` и пересобирает compose. Деплой идёт только если тесты прошли.

**Разовая подготовка сервера:**
```bash
# 1. Клонировать репо в DEPLOY_PATH и один раз поднять вручную (шаги 2–5 выше)
# 2. Создать deploy-ключ для CI:
ssh-keygen -t ed25519 -f ~/deploy_key -N ""
cat ~/deploy_key.pub >> ~/.ssh/authorized_keys   # публичный — на сервер
# приватный ~/deploy_key -> в секрет SSH_KEY (целиком, включая BEGIN/END)
```

**Secrets в GitHub** (Settings → Secrets and variables → Actions):

| Secret | Значение |
|---|---|
| `SSH_HOST` | IP/домен сервера |
| `SSH_USER` | пользователь (напр. `deploy`) |
| `SSH_KEY` | приватный ключ `~/deploy_key` целиком |
| `SSH_PORT` | (опц.) SSH-порт, по умолчанию 22 |
| `DEPLOY_PATH` | путь к репо на сервере, напр. `/srv/tg-channel-studio` |

> На сервере должен быть доступ `git pull` без пароля (deploy-ключ репозитория или https-токен)
> и установленный Docker для пользователя `SSH_USER` (добавь его в группу `docker`).
> Ручной деплой по кнопке — вкладка Actions → Deploy → Run workflow.

---

## Managed-альтернативы (если не хочешь VPS)
- **Frontend/Marketing** → Vercel (два проекта). На дашборде задай `API_URL` на адрес backend; на лендинге — `NEXT_PUBLIC_SITE_URL`/`NEXT_PUBLIC_APP_URL`.
- **Backend + воркеры** → Railway/Render/Fly.io: один web-сервис (uvicorn) + 3 worker-сервиса из того же образа (команды `python -m app.workers.*`).
- **Postgres/Redis** → managed (Neon/Supabase/Railway, Upstash).
- **userbot-сессию** придётся авторизовать один раз и положить на персистентный диск воркера.
- Stripe webhook URL укажи на публичный адрес backend (`.../api/billing/webhook`).
