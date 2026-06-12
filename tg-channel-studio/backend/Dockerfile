FROM python:3.12-slim

WORKDIR /srv

COPY pyproject.toml ./
COPY app ./app
COPY alembic.ini ./
COPY alembic ./alembic

RUN pip install --no-cache-dir .

# Media transfer scratch dir (donor photos downloaded by ingest, sent by publisher).
ENV MEDIA_DIR=/srv/media
RUN mkdir -p /srv/media

EXPOSE 8000

# Default command — API server. Workers override the command in docker-compose.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
