# Database Schema

Source of truth: `src/database/scripts/schema.sql`. See
[`06_database_design.md`](06_database_design.md) for the ERD diagram and the
agent/tool request-flow diagram. See [`../src/embedding/db_diagrams.md`](../src/embedding/db_diagrams.md)
for the same reference content as indexed knowledge-base text (what the
agent's `search_knowledge_base` tool retrieves for schema questions).

PostgreSQL (Neon). Star-schema layout: `sales` is the fact table;
`regions`, `products`, `customers` are dimension tables.

## `regions`

| Column | Type | Constraints |
|---|---|---|
| `region_id` | `SERIAL` | Primary key |
| `region_name` | `VARCHAR(100)` | `NOT NULL`, `UNIQUE` |
| `country` | `VARCHAR(100)` | `NOT NULL` |

## `products`

| Column | Type | Constraints |
|---|---|---|
| `product_id` | `SERIAL` | Primary key |
| `product_name` | `VARCHAR(150)` | `NOT NULL` |
| `category` | `VARCHAR(100)` | `NOT NULL` |
| `unit_cost` | `NUMERIC(12,2)` | `NOT NULL`, `>= 0` |
| `unit_price` | `NUMERIC(12,2)` | `NOT NULL`, `>= 0` |

## `customers`

| Column | Type | Constraints |
|---|---|---|
| `customer_id` | `SERIAL` | Primary key |
| `customer_name` | `VARCHAR(150)` | `NOT NULL` |
| `segment` | `VARCHAR(50)` | `NOT NULL` (`Enterprise` / `SMB` / `Individual`) |
| `region_id` | `INTEGER` | `NOT NULL`, `REFERENCES regions(region_id)` — the customer's home region |

## `sales` (fact table)

| Column | Type | Constraints |
|---|---|---|
| `sale_id` | `SERIAL` | Primary key |
| `product_id` | `INTEGER` | `NOT NULL`, `REFERENCES products(product_id)` |
| `customer_id` | `INTEGER` | `NOT NULL`, `REFERENCES customers(customer_id)` |
| `region_id` | `INTEGER` | `NOT NULL`, `REFERENCES regions(region_id)` — where the sale occurred (not necessarily the customer's home region) |
| `sale_date` | `DATE` | `NOT NULL` |
| `quantity` | `INTEGER` | `NOT NULL`, `> 0` |
| `unit_price` | `NUMERIC(12,2)` | `NOT NULL`, `>= 0` (price at transaction time) |
| `unit_cost` | `NUMERIC(12,2)` | `NOT NULL`, `>= 0` (cost at transaction time) |
| `revenue` | `NUMERIC(14,2)` | `GENERATED ALWAYS AS (quantity * unit_price) STORED` |
| `profit` | `NUMERIC(14,2)` | `GENERATED ALWAYS AS (quantity * (unit_price - unit_cost)) STORED` |

`revenue`/`profit` are never written directly — always derived.

## Indexes

`customers.region_id`, and on `sales`: `product_id`, `customer_id`,
`region_id`, `sale_date` — the join/filter columns every DAO query in
`src/database/dao/*.py` uses.

## Key metric formulas

- Revenue: `SUM(sales.revenue)`
- Profit: `SUM(sales.profit)`
- Profit margin %: `SUM(sales.profit) / NULLIF(SUM(sales.revenue), 0) * 100`
- Average order value: `SUM(sales.revenue) / COUNT(sales.sale_id)`

## Seed data

`src/database/mock_data/sample_data.sql` — loaded by `init_db.py`:

- 4 regions (North America/USA, Europe/Germany, Asia/Vietnam, South America/Brazil)
- 8 products across `Electronics`/`Accessories`
- 10 customers across the 4 regions and 3 segments
- 70 sales rows, Jan-Jun 2024, one purchase per customer per month plus a
  March "Keyboard" filler order for every customer. Laptop volume is
  deliberately weighted toward the Asia customers (Stark Traders / Wonka
  Distributors) so "top products in Asia" questions have a clear,
  checkable answer.

## Initializing the database

```bash
# from src/
python database/scripts/init_db.py
```

Drops and recreates all 4 tables (safe to re-run), loads the seed data,
then prints row counts to verify.
