-- Database Layer - Mock/sample data for regions, products, customers, sales
--
-- Assumes a freshly recreated schema (see schema.sql) so SERIAL ids are
-- predictable: regions 1-10, products 1-15, customers generated (300 rows).
-- Run via: python database/scripts/init_db.py (from src/)

-- Regions -------------------------------------------------------------
INSERT INTO regions (region_name, country) VALUES
('Oceania','Australia'),
('Middle East','UAE'),
('Africa','South Africa'),
('East Asia','Japan'),
('South Asia','India'),
('Western Europe','France'),
('Northern Europe','UK'),
('Central America','Mexico'),
('Eastern Europe','Poland'),
('Central Asia','Kazakhstan');

-- Products --------------------------------------------------------------
INSERT INTO products (product_name, category, unit_cost, unit_price) VALUES
('Smartphone','Electronics',350,699),
('Server','Infrastructure',2500,4200),
('Storage NAS','Infrastructure',800,1450),
('Router','Networking',120,260),
('Switch','Networking',180,380),
('Projector','Electronics',500,950),
('Mouse','Accessories',12,30),
('Docking Station','Accessories',60,145),
('Security Suite','Software',35,120),
('Cloud Subscription','Software',20,59),
('UPS','Infrastructure',200,450),
('Firewall Appliance','Networking',500,1200),
('Webcam','Accessories',22,60),
('Microphone','Accessories',35,85),
('AI Subscription','Software',50,199);

-- Customers (region_id references the regions above) --------------------
INSERT INTO customers
(customer_name, segment, region_id)
SELECT
    'Customer_' || gs,
    CASE
        WHEN random() < 0.4 THEN 'Enterprise'
        WHEN random() < 0.8 THEN 'SMB'
        ELSE 'Individual'
    END,
    floor(random()*10 + 1)::int
FROM generate_series(1,300) gs;

-- Sales -------------------------------------------------------------------
-- One purchase per customer per month (Jan-Jun 2024), quantities trending
-- upward, plus a Keyboard filler order for every customer in March.
-- Laptop volume is deliberately weighted toward the Asia customers
-- (Stark Traders / Wonka Distributors) to mirror the "Laptop dominates
-- Asia revenue" narrative in docs/business_description.md > Example Conversation.
INSERT INTO sales
(
    product_id,
    customer_id,
    region_id,
    sale_date,
    quantity,
    unit_price,
    unit_cost
)
SELECT
    p.product_id,
    c.customer_id,
    c.region_id,
    (
        DATE '2024-01-01'
        + floor(
            random() *
            (
                CURRENT_DATE - DATE '2024-01-01'
            )
        )::int
    ),
    floor(random()*40 + 1)::int,
    p.unit_price,
    p.unit_cost
FROM customers c
JOIN products p ON TRUE
WHERE random() < 0.12;
