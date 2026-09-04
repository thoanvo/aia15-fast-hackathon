-- Database Layer - Schema DDL
-- Tables: Regions, Products, Customers, Sales (docs/business_description.md > Database Schema)
--
-- Run via: python database/scripts/init_db.py (from src/)
-- Safe to re-run: existing tables are dropped and recreated.

DROP TABLE IF EXISTS sales CASCADE;
DROP TABLE IF EXISTS customers CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS regions CASCADE;

CREATE TABLE regions (
    region_id   SERIAL PRIMARY KEY,
    region_name VARCHAR(100) NOT NULL UNIQUE,
    country     VARCHAR(100) NOT NULL
);

CREATE TABLE products (
    product_id   SERIAL PRIMARY KEY,
    product_name VARCHAR(150) NOT NULL,
    category     VARCHAR(100) NOT NULL,
    unit_cost    NUMERIC(12, 2) NOT NULL CHECK (unit_cost >= 0),
    unit_price   NUMERIC(12, 2) NOT NULL CHECK (unit_price >= 0)
);

CREATE TABLE customers (
    customer_id   SERIAL PRIMARY KEY,
    customer_name VARCHAR(150) NOT NULL,
    segment       VARCHAR(50) NOT NULL,
    region_id     INTEGER NOT NULL REFERENCES regions(region_id)
);

-- Fact table: one row per sale transaction.
-- revenue/profit are generated columns so every downstream query
-- (get_top_products, get_profit_analysis, get_summary_kpi, ...) can
-- aggregate them directly without recomputing quantity * price each time.
CREATE TABLE sales (
    sale_id     SERIAL PRIMARY KEY,
    product_id  INTEGER NOT NULL REFERENCES products(product_id),
    customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
    region_id   INTEGER NOT NULL REFERENCES regions(region_id),
    sale_date   DATE NOT NULL,
    quantity    INTEGER NOT NULL CHECK (quantity > 0),
    unit_price  NUMERIC(12, 2) NOT NULL CHECK (unit_price >= 0),
    unit_cost   NUMERIC(12, 2) NOT NULL CHECK (unit_cost >= 0),
    revenue     NUMERIC(14, 2) GENERATED ALWAYS AS (quantity * unit_price) STORED,
    profit      NUMERIC(14, 2) GENERATED ALWAYS AS (quantity * (unit_price - unit_cost)) STORED
);

CREATE INDEX idx_customers_region_id ON customers(region_id);
CREATE INDEX idx_sales_product_id    ON sales(product_id);
CREATE INDEX idx_sales_customer_id   ON sales(customer_id);
CREATE INDEX idx_sales_region_id     ON sales(region_id);
CREATE INDEX idx_sales_sale_date     ON sales(sale_date);
