# SQL Query Idioms

Business-specific SQL idioms used against the schema in
[`db_diagrams.md`](db_diagrams.md) that aren't obvious from the schema or
business-metric formulas alone - narrowed from a full set of example
queries (redundant with live schema reflection + the 16 fixed business
tools) down to the patterns worth having as retrievable, worked examples.

## Idiom: Guarding a Percentage Against Division by Zero

Any percentage computed from a `SUM(...)` denominator (profit margin,
month-over-month growth) must guard against a zero or all-NULL group -
otherwise a filtered/grouped row with no matching sales raises a
division-by-zero error instead of returning `NULL`/`0`:

```sql
SELECT
    p.category,
    SUM(s.revenue) AS total_revenue,
    SUM(s.profit) AS total_profit,
    ROUND((SUM(s.profit) / NULLIF(SUM(s.revenue), 0)) * 100, 2) AS margin_pct
FROM sales s
JOIN products p ON s.product_id = p.product_id
GROUP BY p.category
ORDER BY total_profit DESC;
```

`NULLIF(SUM(s.revenue), 0)` turns a zero denominator into `NULL`, which
makes the division return `NULL` instead of erroring - this pattern
applies anywhere a rate/percentage is computed, not just margin.

## Idiom: Including Dimension Rows With Zero Activity

A `JOIN` (inner join) between a dimension table and `sales` silently
drops any dimension row with no matching sales - e.g. a region that
exists but had zero transactions in the filtered period disappears from
the result entirely, which is usually not what "performance by region"
means. Use `LEFT JOIN` from the dimension table when the question implies
every dimension member should appear, even with zero activity:

```sql
SELECT
    r.region_id,
    r.region_name,
    r.country,
    COUNT(s.sale_id) AS total_transactions,
    SUM(s.revenue) AS total_revenue,
    SUM(s.profit) AS total_profit
FROM regions r
LEFT JOIN sales s ON r.region_id = s.region_id
GROUP BY r.region_id, r.region_name, r.country
ORDER BY total_revenue DESC;
```

With a `LEFT JOIN`, a region with no sales still appears in the result
with `total_transactions = 0` and `total_revenue`/`total_profit = NULL`
(or `0` if wrapped in `COALESCE`) - a plain `JOIN` would omit that row.

## Idiom: Time-Bucketed Trend With Configurable Granularity

`date_trunc(unit, sales.sale_date)` buckets transactions into day/month/
year periods; the bucket unit is the only thing that changes for
"daily"/"monthly"/"yearly" trend questions:

```sql
SELECT
    date_trunc('month', s.sale_date) AS period,
    SUM(s.revenue) AS total_revenue,
    SUM(s.profit) AS total_profit
FROM sales s
GROUP BY period
ORDER BY period;
```

Swap `'month'` for `'day'` or `'year'` per the requested granularity;
everything else about the query stays the same.

## Idiom: Month-over-Month Comparison With a Window Function

Comparing each period to the previous one needs `LAG(...) OVER (ORDER BY
...)`, not a self-join - a self-join on a bucketed value is error-prone
(gaps in months, off-by-one joins) where a window function is exact:

```sql
WITH monthly AS (
    SELECT date_trunc('month', s.sale_date) AS month,
           SUM(s.revenue) AS total_revenue
    FROM sales s
    GROUP BY month
)
SELECT
    month,
    total_revenue,
    LAG(total_revenue) OVER (ORDER BY month) AS previous_revenue,
    ROUND(
        (total_revenue - LAG(total_revenue) OVER (ORDER BY month))
        / NULLIF(LAG(total_revenue) OVER (ORDER BY month), 0) * 100,
        2
    ) AS revenue_growth_pct
FROM monthly
ORDER BY month;
```

Combines both prior idioms: a window function for the period-over-period
comparison, and `NULLIF` to guard the growth-percentage denominator.
