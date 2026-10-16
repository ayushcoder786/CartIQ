from flask import Flask, render_template, request, send_from_directory, jsonify
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime

app = Flask(__name__)
ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "data" / "ecommerce_orders.csv"

def load_data():
    df = pd.read_csv(DATA_PATH, parse_dates=["order_date"])
    df["line_total"] = pd.to_numeric(df["line_total"], errors="coerce").fillna(0)
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(0)
    return df

def customer_metrics(df):
    if df.empty:
        return pd.DataFrame(columns=["customer_id","frequency","monetary","recency","avg_basket","reorder_probability","segment","last_order"])
    order_level = df.groupby(["customer_id","order_id"], as_index=False).agg(
        order_date=("order_date","max"), order_value=("line_total","sum"))
    latest = df["order_date"].max()
    cm = order_level.groupby("customer_id").agg(
        frequency=("order_id","nunique"),
        monetary=("order_value","sum"),
        avg_basket=("order_value","mean"),
        last_order=("order_date","max")
    ).reset_index()
    cm["recency"] = (latest - cm["last_order"]).dt.days.clip(lower=0)
    # Transparent, interpretable heuristic score: not presented as a trained ML model.
    freq_score = np.minimum(cm["frequency"] / 8, 1)
    recent_score = 1 - np.minimum(cm["recency"] / 120, 1)
    spend_score = np.minimum(cm["monetary"] / 500, 1)
    cm["reorder_probability"] = (0.45*recent_score + 0.35*freq_score + 0.20*spend_score).clip(0,1)
    cm["segment"] = np.select(
        [
            (cm["frequency"] >= 5) & (cm["recency"] <= 45) & (cm["monetary"] >= 150),
            (cm["recency"] <= 60) & (cm["frequency"] >= 2),
            (cm["recency"] > 120),
            (cm["frequency"] <= 2) & (cm["monetary"] < 100)
        ],
        ["Champions", "Loyal / Active", "At Risk", "New / Low Frequency"],
        default="Needs Nurturing"
    )
    return cm

def dashboard_data():
    df = load_data()
    cm = customer_metrics(df)
    order_level = df.groupby("order_id", as_index=False).agg(order_value=("line_total","sum"), order_date=("order_date","max"))
    total_revenue = float(df["line_total"].sum())
    reorder_rate = float((cm["reorder_probability"] >= 0.55).mean()*100) if len(cm) else 0
    monthly = df.assign(month=df["order_date"].dt.to_period("M").astype(str)).groupby("month")["line_total"].sum().tail(8)
    category = df.groupby("category")["line_total"].sum().sort_values(ascending=False)
    return df, cm, order_level, {
        "revenue": total_revenue, "orders": int(df["order_id"].nunique()),
        "customers": int(df["customer_id"].nunique()),
        "aov": float(order_level["order_value"].mean()) if len(order_level) else 0,
        "reorder_rate": reorder_rate,
        "avg_frequency": float(cm["frequency"].mean()) if len(cm) else 0,
        "monthly_labels": monthly.index.tolist(), "monthly_values": [round(float(x),2) for x in monthly.values],
        "category_labels": category.index.tolist(), "category_values": [round(float(x),2) for x in category.values],
        "segment_labels": cm["segment"].value_counts().index.tolist(),
        "segment_values": cm["segment"].value_counts().values.tolist()
    }

@app.route("/")
def dashboard():
    df, cm, orders, stats = dashboard_data()
    recent = df.sort_values("order_date", ascending=False).groupby("order_id").first().reset_index().head(7)
    recent_orders = []
    for _, row in recent.iterrows():
        total = float(df.loc[df["order_id"] == row["order_id"], "line_total"].sum())
        recent_orders.append({"id":row["order_id"],"customer":row["customer_id"],"date":row["order_date"].strftime("%d %b %Y"),"value":total,"items":int(df.loc[df["order_id"]==row["order_id"],"quantity"].sum())})
    return render_template("dashboard.html", stats=stats, recent=recent_orders, active="dashboard")

@app.route("/customers")
def customers():
    df, cm, orders, stats = dashboard_data()
    q = request.args.get("q","").strip().upper()
    segment = request.args.get("segment","All")
    sort = request.args.get("sort","frequency")
    if q: cm = cm[cm["customer_id"].str.contains(q, na=False)]
    if segment != "All": cm = cm[cm["segment"] == segment]
    if sort not in cm.columns: sort = "frequency"
    cm = cm.sort_values(sort, ascending=(sort=="recency"))
    records = []
    for _, r in cm.head(250).iterrows():
        records.append({
            "customer_id":r["customer_id"], "frequency":int(r["frequency"]),
            "monetary":float(r["monetary"]), "recency":int(r["recency"]),
            "avg_basket":float(r["avg_basket"]), "prob":float(r["reorder_probability"]*100),
            "segment":r["segment"], "last_order":r["last_order"].strftime("%d %b %Y")
        })
    return render_template("customers.html", customers=records, segments=["All"]+sorted(load_data()["customer_id"].unique().tolist()) if False else ["All","Champions","Loyal / Active","At Risk","New / Low Frequency","Needs Nurturing"], selected_segment=segment, q=q, sort=sort, total=len(cm), active="customers")

@app.route("/reorder")
def reorder():
    df, cm, orders, stats = dashboard_data()
    return render_template("reorder.html", stats=stats, active="reorder")

@app.route("/api/predict", methods=["POST"])
def predict():
    data = request.get_json(silent=True) or request.form
    try:
        frequency = max(0, float(data.get("frequency", 3)))
        recency = max(0, float(data.get("recency", 30)))
        monetary = max(0, float(data.get("monetary", 150)))
        basket = max(0, float(data.get("basket", 45)))
        # Same transparent score family used by the customer table.
        score = (0.45*(1-min(recency/120,1)) + 0.35*min(frequency/8,1) + 0.20*min(monetary/500,1))
        # Slight adjustment for the entered expected basket value.
        score = float(np.clip(score * (0.9 + 0.1*min(basket/100,1)), 0, 1))
        if score >= .70: label, action = "High likelihood", "Offer a relevant add-on or replenishment reminder."
        elif score >= .45: label, action = "Medium likelihood", "Use a modest incentive and personalized recommendations."
        else: label, action = "Low likelihood", "Try a win-back message; avoid repeated discounting."
        return jsonify({"probability":round(score*100,1),"label":label,"action":action,"expected_basket":round(basket,2),"expected_revenue":round(score*basket,2)})
    except (ValueError, TypeError):
        return jsonify({"error":"Enter valid non-negative numeric values."}), 400

@app.route("/download-dataset")
def download_dataset():
    return send_from_directory(DATA_PATH.parent, DATA_PATH.name, as_attachment=True)

@app.route("/api/summary")
def api_summary():
    _, _, _, stats = dashboard_data()
    return jsonify(stats)

if __name__ == "__main__":
    app.run(debug=True)
