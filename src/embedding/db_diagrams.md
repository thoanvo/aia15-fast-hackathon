# Database Diagrams & Schema Documentation

## Overview

The database is a PostgreSQL (Neon) relational database supporting the
Database Query Assistant's business intelligence and sales analytics
questions. It tracks sales transactions across geographic regions, product
categories, and customer segments. Star-schema layout: `sales` is the fact
table; `regions`, `products`, `customers` are dimension tables.

## Entity Relationships

```
┌─────────────────┐       ┌──────────────────┐
│     regions     │       │     customers     │
├─────────────────┤       ├──────────────────┤
│ region_id (PK)  │◄──┐   │ customer_id (PK) │
│ region_name     │   │   │ customer_name    │
│ country         │   │   │ segment          │
└─────────────────┘   │   │ region_id (FK)   ├──┐
                       └───┤                  │  │
                           └──────────────────┘  │
                                                  │
┌─────────────────┐                              │
│     products     │       ┌──────────────────┐  │
├─────────────────┤       │       sales        │  │
│ product_id (PK) │◄──────┤ sale_id (PK)      │  │
│ product_name    │       │ product_id (FK)   │  │
│ category        │       │ customer_id (FK)  ├──┘
│ unit_cost       │       │ region_id (FK)    │◄── regions
│ unit_price      │       │ sale_date         │
└─────────────────┘       │ quantity          │
                          │ unit_price        │
                          │ unit_cost         │
                          │ revenue (generated)│
                          │ profit  (generated)│
                          └──────────────────┘
```

Key relationship semantics not obvious from the diagram alone:
- `customers.region_id` (a customer's home region) is independent of
  `sales.region_id` (where a specific transaction occurred) - no
  constraint links them, and they are frequently different. A query
  filtering "sales in Asia" should use `sales.region_id`, not join
  through `customers.region_id`, unless the question is specifically
  about customers' home regions.
- `sales` is the only fact table; every business question ultimately
  aggregates `sales` rows, optionally joined to one or more dimension
  tables for filtering/grouping.

## Table: regions

Geographical market regions - a dimension table for filtering/grouping
`sales` by where a transaction occurred.
- `region_id` (PK): unique identifier.
- `region_name`: e.g. 'North America', 'Europe', 'Asia', 'South America'.
- `country`: representative country for the region, e.g. 'USA', 'Germany',
  'Vietnam', 'Brazil'.

## Table: products

Product catalog, including pricing and unit cost at catalog level (a
sale's own `unit_price`/`unit_cost` may differ - see the `sales` table
below).
- `product_id` (PK): unique identifier.
- `product_name`: e.g. 'Laptop', 'Printer', 'Monitor', 'Scanner', 'Camera',
  'Tablet', 'Keyboard', 'Headset'.
- `category`: e.g. 'Electronics', 'Accessories'.
- `unit_cost` / `unit_price`: current catalog cost/price, not
  necessarily what a historical sale transacted at.

## Table: customers

Customer profile and segmentation.
- `customer_id` (PK): unique identifier.
- `customer_name`: full name or business entity name.
- `segment`: customer classification, e.g. 'Enterprise', 'SMB',
  'Individual' - the usual grouping dimension for segment-performance
  questions.
- `region_id` (FK -> regions): the customer's home region. Not the same
  thing as a given sale's region - see "Entity Relationships" above.

## Table: sales

Fact table recording every sales transaction - the table nearly every
business question aggregates.
- `sale_id` (PK): unique transaction identifier.
- `product_id` / `customer_id` / `region_id` (FKs): what was sold, to
  whom, and in which region the transaction occurred.
- `sale_date`: transaction date (YYYY-MM-DD) - the column used for date
  filters, trend bucketing, and month-over-month growth.
- `quantity`: units purchased.
- `unit_price` / `unit_cost`: price/cost *at transaction time* - may
  differ from the product's current catalog price/cost, since prices
  change over time but historical transactions keep what was charged
  then.
- `revenue` (generated, `quantity * unit_price`): never written
  directly, always derived - use this column rather than recomputing
  revenue from `quantity * unit_price` yourself.
- `profit` (generated, `quantity * (unit_price - unit_cost)`): same -
  always derived, never written directly.

## Metric: Revenue

`SUM(sales.revenue)` - total revenue over the filtered/grouped rows.
`sales.revenue` is already `quantity * unit_price`; do not re-multiply.

## Metric: Profit

`SUM(sales.profit)` - total profit over the filtered/grouped rows.
`sales.profit` is already `quantity * (unit_price - unit_cost)`; do not
re-derive it from cost/price columns.

## Metric: Profit Margin

`SUM(sales.profit) / NULLIF(SUM(sales.revenue), 0) * 100` - always guard
the denominator with `NULLIF` to avoid a division-by-zero error when a
filtered group has zero revenue (e.g. a region/category with no sales in
the selected date range).

## Metric: Average Order Value (AOV)

`SUM(sales.revenue) / COUNT(sales.sale_id)` - average revenue per
transaction, not per customer or per product.

## Metric: Month-over-Month Revenue Growth

`(revenue_month_t - revenue_month_t-1) / NULLIF(revenue_month_t-1, 0) * 100`
- compute per-month revenue first (bucket `sales.sale_date` by month),
then compare consecutive months; guard the denominator with `NULLIF` the
same way as profit margin.

## Query Shape Reference

Quick reference for which table(s) a business question shape typically
joins - useful background when a question doesn't match a fixed business
tool and a query needs to be written from scratch.

| Business question shape | Tables joined |
|---|---|
| Top products by revenue/quantity/profit, optionally by region | `sales` + `products` (+ `regions` if filtered) |
| Top customers by revenue | `sales` + `customers` (+ `regions`) |
| Region performance / regional breakdown | `sales` + `regions` |
| Sales trend over time (day/month/year) | `sales` (+ `regions` if filtered) |
| Profit analysis by product/customer/region | `sales` + the matching dimension table |
| Customer purchase history | `sales` + `customers` + `products` |
| Category / segment performance | `sales` + `products` (category) or `customers` (segment) |
| Overall KPI summary (revenue/profit/margin/orders) | `sales` only |
