#!/bin/sh
set -e

# Render's free tier can restart the container (e.g. after a period of
# inactivity) without necessarily wiping the disk, but a genuine redeploy
# does reset it. Either way, this must be idempotent: only bootstrap from
# the committed extraction JSON if there's no database yet. If we reseeded
# unconditionally on every start, any reports uploaded live via "Upload
# Report" would get wiped out the next time the free-tier service woke up
# from an idle spin-down — defeating the whole point of the dynamic upload
# feature.
DB_PATH="/app/app/senus.db"

if [ ! -f "$DB_PATH" ]; then
  echo "[entrypoint] No existing database found at $DB_PATH — seeding from committed extraction..."
  python -m app.seed
else
  echo "[entrypoint] Existing database found at $DB_PATH — skipping seed, keeping live data."
fi

# Render injects $PORT; default to 8000 for local `docker run` without it.
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"