"""
E-commerce Sales & Customer Retention Analysis
------------------------------------------------
Steps: 1) load  2) clean  3) KPIs  4) sales trends  5) category profitability
       6) channel quality  7) delivery vs satisfaction  8) cohort retention
       9) RFM customer segmentation  -> charts saved to ../images/, tables to ../outputs/

Run:  python scripts/analysis.py
"""
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA, IMG, OUT = ROOT / "data", ROOT / "images", ROOT / "outputs"
IMG.mkdir(exist_ok=True)
OUT.mkdir(exist_ok=True)

# ---------- chart style ----------
BLUE, ORANGE, GREY = "#2a78d6", "#eb6834", "#b8b7b2"
INK, INK2, SURFACE = "#0b0b0b", "#52514e", "#fcfcfb"
plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": GREY, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": "#e6e5e0", "grid.linewidth": 0.8,
    "axes.titleweight": "bold", "axes.titlesize": 13, "axes.titlecolor": INK,
    "axes.titlelocation": "left", "font.size": 10,
})


def save(fig, name):
    fig.tight_layout()
    fig.savefig(IMG / name, dpi=150)
    plt.close(fig)


# =============== 1. LOAD ===============
customers = pd.read_csv(DATA / "customers.csv", parse_dates=["signup_date"])
products = pd.read_csv(DATA / "products.csv")
orders = pd.read_csv(DATA / "orders.csv", parse_dates=["order_date"])
items = pd.read_csv(DATA / "order_items.csv")

# =============== 2. CLEAN ===============
print("---- Data cleaning ----")
print("Duplicate order_item rows:", items.duplicated().sum())
items = items.drop_duplicates()
print("Missing ages:", customers["age"].isna().sum(), "-> filled with median")
customers["age"] = customers["age"].fillna(customers["age"].median())
print("Region values before fix:", sorted(customers["region"].unique()))
customers["region"] = customers["region"].str.strip().str.title()

# Build one analysis table at line level
df = (items.merge(products, on="product_id")
           .merge(orders, on="order_id")
           .merge(customers, on="customer_id"))
df["revenue"] = df["quantity"] * df["unit_price"] * (1 - df["discount"])
df["profit"] = df["quantity"] * (df["unit_price"] * (1 - df["discount"]) - df["unit_cost"])
sales = df[df["status"] == "Delivered"].copy()
sales["month"] = sales["order_date"].dt.to_period("M")

# =============== 3. KPIs ===============
n_orders = sales["order_id"].nunique()
kpi = {
    "Revenue": sales["revenue"].sum(),
    "Profit": sales["profit"].sum(),
    "Profit margin %": 100 * sales["profit"].sum() / sales["revenue"].sum(),
    "Orders": n_orders,
    "Avg order value": sales["revenue"].sum() / n_orders,
    "Customers": sales["customer_id"].nunique(),
    "Return rate %": 100 * (orders["status"] == "Returned").mean(),
}
print("\n---- KPIs ----")
for k, v in kpi.items():
    print(f"{k:>18}: {v:,.2f}")

# =============== 4. MONTHLY TREND ===============
monthly = sales.groupby("month")["revenue"].sum()
fig, ax = plt.subplots(figsize=(10, 4))
x = monthly.index.to_timestamp()
ax.plot(x, monthly.values / 1000, color=BLUE, lw=2, marker="o", ms=4)
for m in ["2023-11", "2024-11"]:
    ts = pd.Period(m).to_timestamp()
    ax.annotate(f"Nov peak\n${monthly[pd.Period(m)]/1000:,.0f}K",
                (ts, monthly[pd.Period(m)] / 1000), xytext=(0, 12),
                textcoords="offset points", ha="center", color=INK2, fontsize=9)
ax.set_title("Monthly revenue (delivered orders) - clear Nov/Dec seasonality")
ax.set_ylabel("Revenue ($K)")
ax.yaxis.set_major_formatter(mtick.StrMethodFormatter("${x:,.0f}K"))
ax.set_ylim(0, monthly.max() / 1000 * 1.25)
save(fig, "01_monthly_revenue.png")

# =============== 5. CATEGORY PROFITABILITY ===============
cat = sales.groupby("category")[["revenue", "profit"]].sum()
cat["margin_pct"] = 100 * cat["profit"] / cat["revenue"]
cat["revenue_share_pct"] = 100 * cat["revenue"] / cat["revenue"].sum()
cat["profit_share_pct"] = 100 * cat["profit"] / cat["profit"].sum()
cat = cat.sort_values("revenue", ascending=True)
cat.round(1).to_csv(OUT / "category_profitability.csv")

fig, ax = plt.subplots(figsize=(9, 4.5))
y = np.arange(len(cat))
h = 0.38
ax.barh(y + h / 2, cat["revenue_share_pct"], h, color=BLUE, label="Share of revenue")
ax.barh(y - h / 2, cat["profit_share_pct"], h, color=ORANGE, label="Share of profit")
ax.set_yticks(y, [f"{c}  ({m:.0f}% margin)" for c, m in zip(cat.index, cat["margin_pct"])])
ax.xaxis.set_major_formatter(mtick.PercentFormatter())
ax.set_title("Electronics brings half the revenue but a fraction of the profit")
ax.legend(frameon=False, loc="lower right")
ax.grid(axis="y", visible=False)
save(fig, "02_category_revenue_vs_profit.png")

# =============== 6. ACQUISITION CHANNEL QUALITY ===============
cust = (sales.groupby(["customer_id", "acquisition_channel"])
             .agg(orders=("order_id", "nunique"), spend=("revenue", "sum"))
             .reset_index())
chan = cust.groupby("acquisition_channel").agg(
    customers=("customer_id", "count"),
    avg_orders=("orders", "mean"),
    avg_ltv=("spend", "mean"),
    repeat_rate_pct=("orders", lambda s: 100 * (s > 1).mean()),
).sort_values("avg_ltv")
chan.round(2).to_csv(OUT / "channel_quality.csv")

fig, ax = plt.subplots(figsize=(9, 4))
colors = [ORANGE if c == "Paid Ads" else BLUE for c in chan.index]
ax.barh(chan.index, chan["avg_ltv"], color=colors, height=0.6)
for i, (v, r) in enumerate(zip(chan["avg_ltv"], chan["repeat_rate_pct"])):
    ax.text(v + 15, i, f"${v:,.0f}  |  {r:.0f}% repeat", va="center", color=INK2, fontsize=9)
ax.set_xlim(0, chan["avg_ltv"].max() * 1.35)
ax.xaxis.set_major_formatter(mtick.StrMethodFormatter("${x:,.0f}"))
ax.set_title("Customer lifetime value by acquisition channel")
ax.grid(axis="y", visible=False)
save(fig, "03_channel_ltv.png")

# =============== 7. DELIVERY SPEED vs SATISFACTION ===============
deliv = orders[orders["status"] == "Delivered"].copy()
deliv["bucket"] = pd.cut(deliv["delivery_days"], [0, 3, 5, 7, 100],
                         labels=["1-3 days", "4-5 days", "6-7 days", "8+ days"])
d = deliv.groupby("bucket", observed=True).agg(
    orders=("order_id", "count"),
    avg_review=("review_score", "mean"),
    bad_review_pct=("review_score", lambda s: 100 * (s <= 2).mean()))
d.round(2).to_csv(OUT / "delivery_vs_reviews.csv")

fig, ax = plt.subplots(figsize=(8, 4))
ax.bar(d.index.astype(str), d["bad_review_pct"],
       color=[BLUE, BLUE, BLUE, ORANGE], width=0.6)
for i, v in enumerate(d["bad_review_pct"]):
    ax.text(i, v + 0.3, f"{v:.1f}%", ha="center", color=INK2)
ax.yaxis.set_major_formatter(mtick.PercentFormatter())
ax.set_title("Share of 1-2 star reviews by delivery time")
ax.set_xlabel("Delivery time")
ax.grid(axis="x", visible=False)
save(fig, "04_delivery_vs_bad_reviews.png")

region = (deliv.merge(customers[["customer_id", "region"]], on="customer_id")
               .groupby("region").agg(avg_delivery_days=("delivery_days", "mean"),
                                      avg_review=("review_score", "mean"))
               .sort_values("avg_delivery_days", ascending=False))
region.round(2).to_csv(OUT / "region_delivery.csv")
print("\n---- Delivery by region ----\n", region.round(2))

# =============== 8. COHORT RETENTION ===============
o = orders[orders["status"] != "Cancelled"].copy()
o["order_month"] = o["order_date"].dt.to_period("M")
o["cohort"] = o.groupby("customer_id")["order_month"].transform("min")
o["age_m"] = (o["order_month"] - o["cohort"]).apply(lambda x: x.n)
cohort = (o.groupby(["cohort", "age_m"])["customer_id"].nunique().unstack(fill_value=0))
retention = cohort.div(cohort[0], axis=0) * 100
ret = retention.loc[:"2024-06", list(range(0, 13))]   # cohorts with >= 6 months of history
# blank out months that haven't happened yet for recent cohorts
months_observed = (pd.Period("2024-12") - ret.index).map(lambda x: x.n).values[:, None]
show = ret.where(ret.columns.values[None, :] <= months_observed)
show.round(1).to_csv(OUT / "cohort_retention.csv")
print("\nAvg month-1 retention: %.1f%% | avg month-6 retention: %.1f%%"
      % (show[1].mean(), show[6].mean()))

fig, ax = plt.subplots(figsize=(11, 6))
im = ax.imshow(show.values, cmap="Blues", vmin=0, vmax=40, aspect="auto")
for i in range(show.shape[0]):
    for j in range(1, show.shape[1]):
        v = show.values[i, j]
        if not np.isnan(v):
            ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=7,
                    color="white" if v > 25 else INK2)
ax.set_xticks(range(show.shape[1]), [f"M{m}" for m in show.columns])
ax.set_yticks(range(show.shape[0]), [str(p) for p in show.index])
ax.set_xlabel("Months since first purchase")
ax.set_ylabel("First-purchase cohort")
ax.set_title("Cohort retention: % of customers buying again (M0 = 100%)")
ax.grid(False)
fig.colorbar(im, ax=ax, format=mtick.PercentFormatter(), shrink=0.8)
save(fig, "05_cohort_retention.png")

# =============== 9. RFM SEGMENTATION ===============
snapshot = sales["order_date"].max() + pd.Timedelta(days=1)
rfm = sales.groupby("customer_id").agg(
    recency=("order_date", lambda s: (snapshot - s.max()).days),
    frequency=("order_id", "nunique"),
    monetary=("revenue", "sum"))
rfm["R"] = pd.qcut(rfm["recency"], 4, labels=[4, 3, 2, 1]).astype(int)
rfm["F"] = pd.qcut(rfm["frequency"].rank(method="first"), 4, labels=[1, 2, 3, 4]).astype(int)
rfm["M"] = pd.qcut(rfm["monetary"], 4, labels=[1, 2, 3, 4]).astype(int)


def segment(r):
    if r.R >= 3 and r.F >= 3 and r.M >= 3:
        return "Champions"
    if r.R >= 3 and r.F >= 2:
        return "Loyal / Potential"
    if r.R <= 2 and r.F >= 3:
        return "At Risk (was valuable)"
    if r.R >= 3:
        return "New / Promising"
    return "Lost / Hibernating"


rfm["segment"] = rfm.apply(segment, axis=1)
seg = rfm.groupby("segment").agg(customers=("monetary", "size"),
                                 revenue=("monetary", "sum"),
                                 avg_recency_days=("recency", "mean"))
seg["customer_pct"] = 100 * seg["customers"] / seg["customers"].sum()
seg["revenue_pct"] = 100 * seg["revenue"] / seg["revenue"].sum()
seg = seg.sort_values("revenue_pct")
seg.round(1).to_csv(OUT / "rfm_segments.csv")
rfm.to_csv(OUT / "rfm_customer_scores.csv")
print("\n---- RFM segments ----\n", seg.round(1))

fig, ax = plt.subplots(figsize=(9, 4.5))
y = np.arange(len(seg))
ax.barh(y + h / 2, seg["customer_pct"], h, color=GREY, label="Share of customers")
ax.barh(y - h / 2, seg["revenue_pct"], h, color=BLUE, label="Share of revenue")
ax.set_yticks(y, seg.index)
ax.xaxis.set_major_formatter(mtick.PercentFormatter())
ax.set_title("RFM segments: who our revenue really comes from")
ax.legend(frameon=False, loc="lower right")
ax.grid(axis="y", visible=False)
save(fig, "06_rfm_segments.png")

print("\nCharts saved to images/, tables saved to outputs/")
