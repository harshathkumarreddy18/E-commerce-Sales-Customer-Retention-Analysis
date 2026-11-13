# E-commerce Sales & Customer Retention Analysis

<img width="1350" height="675" alt="02_category_revenue_vs_profit" src="https://github.com/user-attachments/assets/50769358-9d35-41b5-bfdf-d0df46ad42f4" />
<img width="1350" height="600" alt="03_channel_ltv" src="https://github.com/user-attachments/assets/1b5727a9-bc18-4c5e-8869-fa5382b6515b" />
<img width="1200" height="600" alt="04_delivery_vs_bad_reviews" src="https://github.com/user-attachments/assets/62f0b7ce-c2f9-49c6-b5ab-c2f2789c3743" />




## About the Project
This project analyzes 2 years of sales data from an online store (12,000+ orders, $4.1M revenue).
The goal is to understand **where the business makes money, where it loses money, and how to keep customers coming back.**

## Business Questions
- Which product categories bring the most profit?
- Which marketing channel brings the best customers?
- Does slow delivery lead to bad reviews?
- How many customers come back after their first order?
- Which customers should the business target?

## Dataset
Simulated e-commerce data (2023–2024) with 4 tables:
- **customers**: customer details, region, marketing channel
- **products**: category, price, cost
- **orders**: order date, status, delivery days, review score
- **order_items**: products, quantity, discount in each order

## Tools Used
- **SQL**: data analysis with joins, CTEs and window functions
- **Python (Pandas, Matplotlib)**: data cleaning, analysis and charts

## Key Insights
1. **Electronics** brings 54% of revenue but only 22% of profit. **Fashion** is the most profitable category.
2. Customers from **Paid Ads** spend 37% less than customers from **Referrals**.
3. Orders delivered in **8+ days** get 12x more bad reviews.
4. Only **1 in 4** customers buy again after their first month.
5. **1,132 at-risk customers**, worth $1.27M in past sales, can be targeted with a win-back campaign.


## Recommendations
- Promote high-profit categories like Fashion and Beauty
- Spend less on Paid Ads and more on Referral and Email marketing
- Improve delivery speed in the Central region
- Run a win-back campaign for at-risk customers
