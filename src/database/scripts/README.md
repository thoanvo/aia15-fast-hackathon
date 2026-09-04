# database/scripts/

| File | Purpose |
|---|---|
| `schema.sql` | DDL for `regions`, `products`, `customers`, `sales` (drops + recreates — safe to re-run). |
| `init_db.py` | Runs `schema.sql`, then `../mock_data/sample_data.sql`, then prints row counts. Run with `python database/scripts/init_db.py` from `src/`. |
