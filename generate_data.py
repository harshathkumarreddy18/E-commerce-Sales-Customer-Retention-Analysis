"""
Generate a realistic e-commerce dataset (2023-2024) for the analysis.

Tables created in ../data/:
  customers.csv, products.csv, orders.csv, order_items.csv
and a SQLite database ecommerce.db with the same tables (for the SQL queries).

Run:  python scripts/generate_data.py
"""
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

rng = np.random.default_rng(42)
DATA = Path(__file__).resolve().parent.parent / "data"
DATA.mkdir(exist_ok=True)

# ---------------- Customers ----------------
N_CUST = 5000
regions = ["North", "South", "East", "West", "Central"]
channels = ["Organic Search", "Paid Ads", "Social Media", "Email", "Referral"]
customers = pd.DataFrame({
    "customer_id": [f"C{i:05d}" for i in range(1, N_CUST + 1)],
    "signup_date": pd.to_datetime("2023-01-01")
    + pd.to_timedelta(rng.integers(0, 700, N_CUST), unit="D"),
    "region": rng.choice(regions, N_CUST, p=[0.25, 0.20, 0.22, 0.18, 0.15]),
    "acquisition_channel": rng.choice(channels, N_CUST, p=[0.30, 0.28, 0.20, 0.12, 0.10]),
    "age": rng.integers(18, 66, N_CUST),
})

# ---------------- Products ----------------
cat_info = {  # category: (price range, margin)
    "Electronics": ((80, 900), 0.12),
    "Home & Kitchen": ((15, 250), 0.30),
    "Fashion": ((10, 150), 0.45),
    "Beauty": ((5, 80), 0.50),
    "Sports": ((15, 300), 0.28),
    "Books": ((5, 40), 0.20),
}
rows = []
pid = 1
for cat, ((lo, hi), margin) in cat_info.items():
    for _ in range(40):
        price = round(float(rng.uniform(lo, hi)), 2)
        rows.append({
            "product_id": f"P{pid:04d}",
            "category": cat,
            "unit_price": price,
            "unit_cost": round(price * (1 - margin + rng.normal(0, 0.03)), 2),
        })
        pid += 1
products = pd.DataFrame(rows)

# ---------------- Orders ----------------
# Customer "loyalty" drives how many orders they place; paid-ads customers churn more.
channel_loyalty = {"Organic Search": 1.0, "Paid Ads": 0.55, "Social Media": 0.8,
                   "Email": 1.3, "Referral": 1.5}
order_rows, item_rows = [], []
oid = 1
end = pd.Timestamp("2024-12-31")
cat_weights = np.array([0.18, 0.22, 0.25, 0.15, 0.12, 0.08])
cats = list(cat_info)
for c in customers.itertuples():
    lam = 2.2 * channel_loyalty[c.acquisition_channel]
    n_orders = 1 + rng.poisson(lam)
    date = c.signup_date + pd.Timedelta(days=int(rng.integers(0, 15)))
    for _ in range(n_orders):
        if date > end:
            break
        month = date.month
        status = rng.choice(["Delivered", "Returned", "Cancelled"], p=[0.88, 0.08, 0.04])
        delivery_days = int(np.clip(rng.normal(4 if c.region != "Central" else 7, 1.5), 1, 15))
        rating = int(np.clip(round(rng.normal(4.4 - 0.25 * max(delivery_days - 5, 0), 0.8)), 1, 5))
        order_rows.append({
            "order_id": f"O{oid:06d}", "customer_id": c.customer_id,
            "order_date": date.normalize(), "status": status,
            "delivery_days": delivery_days, "review_score": rating,
        })
        # seasonality: more items in Nov/Dec
        n_items = 1 + rng.poisson(1.6 if month in (11, 12) else 0.8)
        for _ in range(n_items):
            cat = rng.choice(cats, p=cat_weights)
            prod = products[products.category == cat].sample(1, random_state=int(rng.integers(1e9))).iloc[0]
            discount = rng.choice([0, 0.05, 0.10, 0.20], p=[0.6, 0.2, 0.15, 0.05])
            item_rows.append({
                "order_id": f"O{oid:06d}", "product_id": prod.product_id,
                "quantity": int(1 + rng.poisson(0.3)), "discount": discount,
            })
        oid += 1
        # bad experiences make the next order later (or never)
        gap = rng.exponential(75 if rating >= 4 else 160)
        date = date + pd.Timedelta(days=int(gap) + 1)
        if rating <= 2 and rng.random() < 0.5:
            break

orders = pd.DataFrame(order_rows)
order_items = pd.DataFrame(item_rows)

# ---- inject a few real-world data-quality issues to clean in the analysis ----
dup = order_items.sample(40, random_state=1)
order_items = pd.concat([order_items, dup], ignore_index=True)          # duplicate rows
customers.loc[customers.sample(60, random_state=2).index, "age"] = np.nan  # missing ages
customers.loc[customers.sample(30, random_state=3).index, "region"] = "north"  # bad casing

for name, df in {"customers": customers, "products": products,
                 "orders": orders, "order_items": order_items}.items():
    df.to_csv(DATA / f"{name}.csv", index=False)

with sqlite3.connect(DATA / "ecommerce.db") as con:
    for name, df in {"customers": customers, "products": products,
                     "orders": orders, "order_items": order_items}.items():
        df.to_sql(name, con, if_exists="replace", index=False)

print(f"customers={len(customers)}, products={len(products)}, "
      f"orders={len(orders)}, order_items={len(order_items)}")
