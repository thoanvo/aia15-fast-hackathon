# database/connection/

`connection_pool.py`:

- `engine` — SQLAlchemy engine built from `config.settings.DATABASE_URL`
  (`pool_size=5`, `max_overflow=10`, `pool_pre_ping=True`).
- `get_session()` — context manager used by every DAO function; commits on
  success, rolls back on error, always closes.
- `check_connection()` — basic `SELECT 1` health check, used by the
  backend's `/health/db` endpoint (Phase 5).
- `serialize_row(mapping)` — converts a SQLAlchemy `RowMapping` into a plain
  JSON-friendly dict (`Decimal` → `float`, `date`/`datetime` → ISO string),
  used by every DAO so results are ready for the LangChain agent's tools
  (Phase 3).
