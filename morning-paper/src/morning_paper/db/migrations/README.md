# Database migrations

## Development

The schema is created directly from the SQLAlchemy ORM models via
`repository.init_db()` (which calls `Base.metadata.create_all(engine)`).
This is sufficient for local dev, where the default engine falls back to a
SQLite file at `<PROJECT_ROOT>/.data/morning_paper.db` when `MP_DB_URL` is unset.

```python
from morning_paper.db import get_engine, init_db
init_db(get_engine())
```

## Production (Alembic)

For production Postgres deployments, use Alembic for versioned migrations
instead of `create_all`:

```bash
alembic init migrations
# point alembic.ini's sqlalchemy.url at MP_DB_URL
# set target_metadata = morning_paper.db.schema.Base.metadata in env.py
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```

### pgvector

The `interest_vectors.vector` column uses `pgvector.sqlalchemy.Vector(1024)`
when pgvector is installed (Voyage `voyage-multilingual-2` dimensionality is
1024); otherwise it degrades to a JSON column so SQLite works.

Postgres requires the extension to be enabled before the vector column can be
created. Add this to the first migration (or run it once by hand):

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```
