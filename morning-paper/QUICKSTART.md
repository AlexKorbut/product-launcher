# Morning Paper — Quickstart

Персональная печатная газета: собирает твои интересы из разных независимых
источников, отбирает и пересказывает/переводит новости и верстает их в настоящую
газету (PDF) в одном из 8 типографских стилей.

## 0. Установка

```bash
cd morning-paper
pip install -e .            # ядро (работает без БД и соцсетей)
pip install -e ".[all]"     # всё опциональное: db, telegram, bot, s3, scheduler
make install-node           # рендерер (Paged.js + Chromium) — нужен для PDF
python scripts/fetch_fonts.py   # OFL-шрифты для всех тем (уже закоммичены, но так обновишь)
cp .env.example .env        # и впиши ключи (см. ниже) — все опциональны для старта
```

Минимум, чтобы увидеть газету прямо сейчас (без ключей, без соцсетей):

```bash
morning-paper list-themes
morning-paper render-proto --theme old-russian --out issue.pdf
```

## 1. Расскажи о своих интересах (любой набор источников, все независимы)

Каждый способ — отдельный подключаемый источник. Можно использовать один или все сразу.

```bash
# а) просто текстом + темами (zero-config, без логина)
morning-paper add-interest --user me \
  --text "ИИ, типографика, Центральная Азия, космос, классическая музыка" \
  --topic технологии --topic культура

# б) markdown-файл с предпочтениями
morning-paper set-interests-file --user me --file my-interests.md

# в) экспорт чата из Telegram Desktop (Settings → Export chat history → JSON)
morning-paper import-telegram-export --user me --file result.json
#    добавь --include-private, если хочешь учитывать и личные переписки

# г) экспорт данных Instagram (Download Your Information, распакованная папка)
morning-paper import-instagram --user me --dir ./instagram-export

# д) живой Telegram (читает твои каналы; нужен TELEGRAM_API_ID/HASH в .env)
morning-paper connect-telegram --user me --phone +49XXXXXX, --use-private-chats
```

Посмотреть, что подключено:

```bash
morning-paper accounts --user me
```

## 2. Настрой стиль, язык, доставку, часовой пояс

```bash
morning-paper set-theme    --user me --theme old-russian   # любой из list-themes
morning-paper set-lang     --user me --lang ru
morning-paper set-delivery --user me --channel file        # file | telegram | email
morning-paper set-tz       --user me --tz Europe/Moscow
```

## 3. Профиль и выпуск

```bash
# профиль интересов (теги через Haiku; нужен ANTHROPIC_API_KEY)
morning-paper build-profile --user me

# полный прогон s1..s8 -> PDF -> доставка
morning-paper run-issue --user me
#   --feed <rss-url>     добавить конкретные ленты
#   --theme / --lang     разово переопределить стиль/язык
#   --from-stage N --until-stage M   гонять отдельные стадии при отладке
```

Без ключей пайплайн не падает: стадии с LLM деградируют (сырой пересказ вместо
переписанного), и ты всё равно получаешь свёрстанный PDF.

## 4. Автоматизация (каждое утро)

```bash
morning-paper schedule --user me --at 05:00          # печатает crontab-строку
morning-paper schedule --user me --at 05:00 --run    # блокирующий планировщик (нужен apscheduler)
```

## Ключи (.env, все опциональны)

| Переменная | Зачем |
|---|---|
| `ANTHROPIC_API_KEY` | теги/пересказ/вёрстка (Haiku/Sonnet/Opus) |
| `VOYAGE_API_KEY` | мультиязычные эмбеддинги интересов |
| `MP_DB_URL` | Postgres+pgvector; если пусто — локальный SQLite |
| `MP_OBJECT_STORE_URL` | `file://...` (по умолчанию) или `s3://bucket/prefix` |
| `TELEGRAM_API_ID` / `TELEGRAM_API_HASH` | живой Telegram (https://my.telegram.org) |
| `TELEGRAM_BOT_TOKEN` | доставка газеты в Telegram-бота |
| `RESEND_API_KEY` | доставка по email |

## Стили (8 тем)

`times-classic` · `economist` · `nyt-modern` · `mono-minimal` ·
`old-russian` (дореволюционный, кириллица) · `vintage` (1920s broadsheet) ·
`art-nouveau` (Belle Époque) · `swiss-grotesk` (Bauhaus/International).

## Приватность

Личные переписки выключены по умолчанию (`--include-private` / `use_private_chats`
включают явно). Из приватного контента извлекаются только интересы — сырой текст не
сохраняется (`is_private=True`, `raw_ref=None`).
```
