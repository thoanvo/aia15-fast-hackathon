# Extended Staging Mock Data

## Purpose

This dataset extends the sample database for staging/testing:

- More regions
- More products
- More customers
- Sales history extended from Jul-2024 through Aug-2026
- Better data distribution for Dynamic-SQL, analytics, ranking, aggregation, filtering and time-series testing

---

## Additional Regions

```sql
INSERT INTO regions (region_name, country) VALUES
('Oceania','Australia'),
('Middle East','UAE'),
('Africa','South Africa'),
('East Asia','Japan'),
('South Asia','India');
```

---

## Additional Products

```sql
INSERT INTO products (product_name, category, unit_cost, unit_price) VALUES
('Smartphone','Electronics',350,699),
('Server','Infrastructure',2500,4200),
('Storage NAS','Infrastructure',800,1450),
('Router','Networking',120,260),
('Switch','Networking',180,380),
('Projector','Electronics',500,950),
('Mouse','Accessories',12,30),
('Docking Station','Accessories',60,145),
('Cloud Subscription','Software',20,59),
('Security Suite','Software',35,120);
```

---

## Additional Customers

```sql
INSERT INTO customers (customer_name, segment, region_id) VALUES
('TechNova Solutions','Enterprise',5),
('Blue Ocean Retail','SMB',5),
('Emirates Digital','Enterprise',6),
('Desert Trading LLC','SMB',6),
('Cape Systems','Enterprise',7),
('Ubuntu Business','SMB',7),
('Sakura Holdings','Enterprise',8),
('Tokyo Commerce','SMB',8),
('Bangalore Innovations','Enterprise',9),
('Mumbai Retail Group','SMB',9),
('Pacific Ventures','Enterprise',5),
('Future Electronics','Individual',8),
('Global Logistics','Enterprise',1),
('Euro Wholesale','Enterprise',2),
('ASEAN Distribution','Enterprise',3),
('LatAm Trading','Enterprise',4);
```

---

## Large Sales Dataset Strategy

Instead of manually inserting thousands of rows, generate staging data.

### PostgreSQL Script

```sql
INSERT INTO sales
(product_id, customer_id, region_id, sale_date, quantity, unit_price, unit_cost)
SELECT
    p.product_id,
    c.customer_id,
    c.region_id,
    d::date,
    (5 + floor(random()*40))::int,
    p.unit_price,
    p.unit_cost
FROM products p
JOIN customers c ON true
JOIN generate_series(
    DATE '2024-07-01',
    DATE '2026-08-31',
    INTERVAL '7 day'
) d ON true
WHERE random() < 0.18;
```

---

## High Revenue Enterprise Sales

```sql
INSERT INTO sales
(product_id, customer_id, region_id, sale_date, quantity, unit_price, unit_cost)
SELECT
    p.product_id,
    c.customer_id,
    c.region_id,
    CURRENT_DATE - ((random()*365)::int),
    (20 + floor(random()*80))::int,
    p.unit_price,
    p.unit_cost
FROM customers c
JOIN products p ON p.category IN ('Infrastructure','Software')
WHERE c.segment='Enterprise'
  AND random() < 0.35;
```

---

## Analytics Test Coverage

Expected volume after generation:

- Regions: 9+
- Products: 18+
- Customers: 25+
- Sales: 3,000-10,000+ rows

Supports testing:

- Top products by revenue
- Revenue by region
- Revenue trend by month
- Customer segmentation
- Distinct customer counts
- Profit margin calculations
- Time-series queries
- Dynamic-SQL aggregation
- Ranking queries
- Pagination and LIMIT validation
- Large result set handling

---

## Recommended Staging Dataset Size

```text
Regions     : 9-15
Products    : 20-50
Customers   : 100-500
Sales       : 10,000-100,000
```

This size is sufficient for Hackathon demos and Dynamic-SQL stress testing.
