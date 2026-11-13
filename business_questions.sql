-- =====================================================================
-- E-commerce Sales & Customer Retention Analysis — SQL (SQLite syntax)
-- Database: data/ecommerce.db
-- Open with DB Browser for SQLite, DBeaver, or:  sqlite3 data/ecommerce.db
-- =====================================================================

-- Q1. What are total revenue, profit, orders and average order value (AOV)?
WITH line AS (
    SELECT DISTINCT oi.order_id, oi.product_id, oi.quantity, oi.discount,
           p.unit_price, p.unit_cost
    FROM order_items oi
    JOIN products p ON p.product_id = oi.product_id
)
SELECT
    ROUND(SUM(l.quantity * l.unit_price * (1 - l.discount)), 2)               AS revenue,
    ROUND(SUM(l.quantity * (l.unit_price * (1 - l.discount) - l.unit_cost)), 2) AS profit,
    COUNT(DISTINCT o.order_id)                                                 AS orders,
    ROUND(SUM(l.quantity * l.unit_price * (1 - l.discount))
          / COUNT(DISTINCT o.order_id), 2)                                     AS avg_order_value
FROM line l
JOIN orders o ON o.order_id = l.order_id
WHERE o.status = 'Delivered';

-- Q2. How does revenue trend month by month? (seasonality)
WITH line AS (
    SELECT DISTINCT oi.order_id, oi.product_id, oi.quantity, oi.discount, p.unit_price
    FROM order_items oi JOIN products p ON p.product_id = oi.product_id
)
SELECT strftime('%Y-%m', o.order_date) AS month,
       ROUND(SUM(l.quantity * l.unit_price * (1 - l.discount)), 2) AS revenue,
       COUNT(DISTINCT o.order_id) AS orders
FROM orders o JOIN line l ON l.order_id = o.order_id
WHERE o.status = 'Delivered'
GROUP BY month
ORDER BY month;

-- Q3. Which categories drive revenue vs. profit? (margin analysis)
WITH line AS (
    SELECT DISTINCT oi.order_id, oi.product_id, oi.quantity, oi.discount,
           p.category, p.unit_price, p.unit_cost
    FROM order_items oi JOIN products p ON p.product_id = oi.product_id
)
SELECT l.category,
       ROUND(SUM(l.quantity * l.unit_price * (1 - l.discount)), 2) AS revenue,
       ROUND(SUM(l.quantity * (l.unit_price * (1 - l.discount) - l.unit_cost)), 2) AS profit,
       ROUND(100.0 * SUM(l.quantity * (l.unit_price * (1 - l.discount) - l.unit_cost))
             / SUM(l.quantity * l.unit_price * (1 - l.discount)), 1) AS margin_pct
FROM line l JOIN orders o ON o.order_id = l.order_id
WHERE o.status = 'Delivered'
GROUP BY l.category
ORDER BY revenue DESC;

-- Q4. Which acquisition channel brings the most valuable customers?
WITH line AS (
    SELECT DISTINCT oi.order_id, oi.product_id, oi.quantity, oi.discount, p.unit_price
    FROM order_items oi JOIN products p ON p.product_id = oi.product_id
),
cust AS (
    SELECT c.customer_id, c.acquisition_channel,
           COUNT(DISTINCT o.order_id) AS n_orders,
           SUM(l.quantity * l.unit_price * (1 - l.discount)) AS spend
    FROM customers c
    JOIN orders o ON o.customer_id = c.customer_id AND o.status = 'Delivered'
    JOIN line l   ON l.order_id = o.order_id
    GROUP BY c.customer_id, c.acquisition_channel
)
SELECT acquisition_channel,
       COUNT(*)                                           AS customers,
       ROUND(AVG(n_orders), 2)                            AS avg_orders,
       ROUND(AVG(spend), 2)                               AS avg_lifetime_value,
       ROUND(100.0 * SUM(n_orders > 1) / COUNT(*), 1)     AS repeat_rate_pct
FROM cust
GROUP BY acquisition_channel
ORDER BY avg_lifetime_value DESC;

-- Q5. Does slow delivery hurt customer satisfaction? (window/bucket analysis)
SELECT CASE WHEN delivery_days <= 3 THEN '1-3 days'
            WHEN delivery_days <= 5 THEN '4-5 days'
            WHEN delivery_days <= 7 THEN '6-7 days'
            ELSE '8+ days' END             AS delivery_bucket,
       COUNT(*)                            AS orders,
       ROUND(AVG(review_score), 2)         AS avg_review,
       ROUND(100.0 * SUM(review_score <= 2) / COUNT(*), 1) AS pct_bad_reviews
FROM orders
WHERE status = 'Delivered'
GROUP BY delivery_bucket
ORDER BY delivery_bucket;

-- Q6. Which regions have delivery problems? (UPPER fixes the 'north' casing issue)
SELECT UPPER(SUBSTR(c.region,1,1)) || LOWER(SUBSTR(c.region,2)) AS region,
       COUNT(*) AS orders,
       ROUND(AVG(o.delivery_days), 1) AS avg_delivery_days,
       ROUND(AVG(o.review_score), 2)  AS avg_review
FROM orders o JOIN customers c ON c.customer_id = o.customer_id
WHERE o.status = 'Delivered'
GROUP BY 1
ORDER BY avg_delivery_days DESC;

-- Q7. Top 10 customers by lifetime spend (RANK window function)
WITH line AS (
    SELECT DISTINCT oi.order_id, oi.product_id, oi.quantity, oi.discount, p.unit_price
    FROM order_items oi JOIN products p ON p.product_id = oi.product_id
),
spend AS (
    SELECT o.customer_id, SUM(l.quantity * l.unit_price * (1 - l.discount)) AS total_spend
    FROM orders o JOIN line l ON l.order_id = o.order_id
    WHERE o.status = 'Delivered'
    GROUP BY o.customer_id
)
SELECT customer_id, ROUND(total_spend, 2) AS total_spend,
       RANK() OVER (ORDER BY total_spend DESC) AS spend_rank
FROM spend
ORDER BY spend_rank
LIMIT 10;

-- Q8. Return rate by category — where are we losing money to returns?
SELECT p.category,
       COUNT(DISTINCT o.order_id) AS orders,
       ROUND(100.0 * COUNT(DISTINCT CASE WHEN o.status = 'Returned' THEN o.order_id END)
             / COUNT(DISTINCT o.order_id), 1) AS return_rate_pct
FROM orders o
JOIN order_items oi ON oi.order_id = o.order_id
JOIN products p     ON p.product_id = oi.product_id
GROUP BY p.category
ORDER BY return_rate_pct DESC;
