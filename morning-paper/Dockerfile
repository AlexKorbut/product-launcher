# Image for the API server and the Celery worker. Both run the full pipeline,
# so it needs Python 3.11+, Node, and the Playwright/Chromium renderer.
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Node 20 (for the Paged.js renderer) + libs Chromium needs at runtime.
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl ca-certificates gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python deps first (layer cache).
COPY pyproject.toml ./
COPY src ./src
RUN pip install -e ".[all]"

# Node renderer + Chromium with its OS deps.
COPY renderer ./renderer
RUN cd renderer && npm install && npx playwright install --with-deps chromium

COPY . .

# Default: API server. The compose `worker` service overrides command.
CMD ["morning-paper", "serve", "--host", "0.0.0.0"]
