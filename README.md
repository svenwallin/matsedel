# matsedel

## SQLite on local disk with S3 backup via Litestream

This project runs SQLite locally in the container and can restore/replicate it to S3 using Litestream.

### How it works

- App database path is `DATABASE_PATH` (default `/app/data/recipes.db` in compose).
- On startup, `run_with_litestream.sh` does:
  1. `litestream restore -if-replica-exists` from S3 to local DB path.
  2. Starts continuous replication with `litestream replicate` while Flask runs.
- If Litestream is disabled, app starts normally and still uses local SQLite.

### Enable it

1. Copy `.env.example` to `.env`.
2. Set:
	- `LITESTREAM_ENABLED=true`
	- `LITESTREAM_S3_BUCKET=<your bucket>`
	- `LITESTREAM_S3_PREFIX=<optional prefix, e.g. matsedel>`
	- `AWS_ACCESS_KEY_ID=<key>`
	- `AWS_SECRET_ACCESS_KEY=<secret>`
	- `AWS_REGION=<region>`
3. Rebuild and start:
	- `podman-compose down`
	- `podman-compose build --no-cache app`
	- `podman-compose up -d`

### Notes

- The app still reads/writes SQLite on local disk for performance and file locking correctness.
- S3 is used for durable replication/restore.