# database/

PostgreSQL (Neon) access: schema, seed data, connection pooling, and DAOs.
See `docs/01_business_requirements.md > Database Layer` for the schema
rationale and [`../../docs/06_database_design.md`](../../docs/06_database_design.md)
for the ERD.

| Folder | Purpose | README |
|---|---|---|
| [`scripts/`](scripts/README.md) | DDL + one-shot init script | [scripts/README.md](scripts/README.md) |
| [`mock_data/`](mock_data/README.md) | Seed data loaded by the init script | [mock_data/README.md](mock_data/README.md) |
| [`connection/`](connection/README.md) | SQLAlchemy engine/session | [connection/README.md](connection/README.md) |
| [`dao/`](dao/README.md) | One module per table/aggregate query | [dao/README.md](dao/README.md) |

## Schema

4 tables: `regions`, `products`, `customers`, `sales` (fact table with
generated `revenue`/`profit` columns). See `scripts/schema.sql` for the DDL.

## One-time setup

```bash
# from src/
python database/scripts/init_db.py
```

Drops and recreates all 4 tables, then loads `mock_data/sample_data.sql`,
then prints row counts to verify.

**Status:** Phase 1 complete — same schema and DAO signatures as the prior
implementation, no LangChain dependency in this layer. Consumed by
`langchain_app/tools/business_tools.py` (Phase 3).
