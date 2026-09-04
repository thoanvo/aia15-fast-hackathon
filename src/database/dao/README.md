# database/dao/

Data access — one module per table/aggregate area. Every function uses
`database.connection.connection_pool.get_session()` and returns plain
dicts/lists via `serialize_row()`. Backs
`langchain_app/tools/business_tools.py` (see that folder's README, Phase 3).

| File | Functions |
|---|---|
| `product_dao.py` | `get_top_products(limit, region=None)` |
| `customer_dao.py` | `get_top_customers(limit, region=None)` |
| `region_dao.py` | `get_region_performance()` |
| `sales_dao.py` | `get_sales_trend(period, region=None)`, `get_profit_analysis(dimension)`, `get_summary_kpi(date_from=None, date_to=None)` |
| `analytics_dao.py` | Product quantity/profit rankings, category/segment performance, product-region performance, customer history, low-margin products, date-range summary, monthly growth, repeat-customer summary |

`period` (day/month/year) and `dimension` (product/customer/region) are
validated against a whitelist before being interpolated into SQL.

Analytics date filters are optional unless the function name requires a
complete date range. Ranking limits are validated by the tool layer and
capped at 100.
