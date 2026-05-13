"""Load HPP.csv, compute dashboard aggregates, and train a lightweight price model."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import Ridge
from sklearn.metrics import r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ROOT = Path(__file__).resolve().parent
CSV_PATH = ROOT / "HPP.csv"

_PROPERTY_TO_CONDITION = {
    "apartment": "Good",
    "villa": "Excellent",
    "independent": "Fair",
}

_CACHE: dict | None = None
_CSV_MTIME: float | None = None
_MODEL_PIPELINE: Pipeline | None = None


def _format_inr_lakhs(price: float) -> str:
    """Format raw price (same units as CSV) as ₹ in Lakhs or Crores."""
    lakhs = price / 100_000.0
    if lakhs >= 100:
        cr = lakhs / 100.0
        return f"₹{cr:.2f} Cr"
    return f"₹{lakhs:.2f} L"


def _format_inr_full(price: float) -> str:
    p = int(round(price))
    return f"₹{p:,}"


def _build_model(df: pd.DataFrame) -> tuple[Pipeline, float]:
    feature_cols = [
        "Area",
        "Bedrooms",
        "Bathrooms",
        "Floors",
        "YearBuilt",
        "Location",
        "Condition",
        "Garage",
    ]
    X = df[feature_cols].copy()
    y = df["Price"].astype(float)

    num = ["Area", "Bedrooms", "Bathrooms", "Floors", "YearBuilt"]
    cat = ["Location", "Condition", "Garage"]

    pre = ColumnTransformer(
        [
            ("num", StandardScaler(), num),
            ("cat", OneHotEncoder(handle_unknown="ignore"), cat),
        ]
    )
    model = Pipeline(
        steps=[
            ("prep", pre),
            ("reg", Ridge(alpha=2.0)),
        ]
    )

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    model.fit(X_train, y_train)
    pred = model.predict(X_test)
    r2 = float(r2_score(y_test, pred))
    return model, r2


def _histogram_bins(prices_lakhs: np.ndarray, bins: int = 12) -> dict:
    counts, edges = np.histogram(prices_lakhs, bins=bins)
    labels = []
    for i in range(len(edges) - 1):
        labels.append(f"{edges[i]:.0f}–{edges[i + 1]:.0f} L")
    return {"labels": labels, "counts": counts.astype(int).tolist()}


def load_dashboard_bundle() -> dict:
    """Return cached dashboard context + trained model (module-level).."""
    global _CACHE, _CSV_MTIME, _MODEL_PIPELINE

    if not CSV_PATH.is_file():
        raise FileNotFoundError(f"Dataset not found: {CSV_PATH}")

    mtime = CSV_PATH.stat().st_mtime
    if _CACHE is not None and _CSV_MTIME == mtime:
        return _CACHE

    df = pd.read_csv(CSV_PATH)
    df["Garage"] = df["Garage"].astype(str).str.strip()
    df["Location"] = df["Location"].astype(str).str.strip()
    df["Condition"] = df["Condition"].astype(str).str.strip()

    _MODEL_PIPELINE, r2_test = _build_model(df)

    n = len(df)
    prices = df["Price"].astype(float)
    prices_lakhs = prices / 100_000.0

    avg_l = float(prices_lakhs.mean())
    max_p = float(prices.max())
    min_p = float(prices.min())

    locations = sorted(df["Location"].unique().tolist())
    loc_avg = (
        df.groupby("Location")["Price"]
        .mean()
        .reindex(locations)
        .astype(float)
        .tolist()
    )
    loc_avg_lakhs = [p / 100_000.0 for p in loc_avg]

    # Trend by year: aggregate mean price per YearBuilt for a rolling recent window
    by_year = (
        df.groupby("YearBuilt", as_index=False)["Price"]
        .mean()
        .sort_values("YearBuilt")
    )
    max_year = int(by_year["YearBuilt"].max())
    min_year_plot = max(int(by_year["YearBuilt"].min()), max_year - 14)
    trend = by_year[by_year["YearBuilt"] >= min_year_plot]
    trend_labels = trend["YearBuilt"].astype(int).tolist()
    trend_values = (trend["Price"] / 100_000.0).astype(float).tolist()

    hist = _histogram_bins(prices_lakhs.values)

    # Donut: bucket by bedroom count (proxy for property segment)
    def bed_bucket(b: int) -> str:
        if b <= 1:
            return "Compact (1 BR)"
        if b <= 3:
            return "Mid (2–3 BR)"
        return "Large (4+ BR)"

    df = df.copy()
    df["_seg"] = df["Bedrooms"].apply(bed_bucket)
    seg_counts = df["_seg"].value_counts()
    donut_labels = seg_counts.index.tolist()
    donut_values = seg_counts.astype(int).tolist()

    scatter_sample = df.sample(n=min(400, len(df)), random_state=42)
    scatter_pts = [
        {"x": float(r.Area), "y": float(r.Price) / 100_000.0}
        for r in scatter_sample.itertuples(index=False)
    ]

    corr = float(df["Area"].corr(df["Price"]))

    # Regression line for Area (x) vs Price lakhs (y)
    slope, intercept = np.polyfit(df["Area"].astype(float), prices_lakhs, 1)
    area_min = float(df["Area"].min())
    area_max = float(df["Area"].max())
    line_pts = [
        {"x": area_min, "y": float(slope * area_min + intercept)},
        {"x": area_max, "y": float(slope * area_max + intercept)},
    ]

    recent = df.sort_values("Id", ascending=False).head(8)
    recent_rows = []
    for r in recent.itertuples(index=False):
        prop_label = bed_bucket(int(r.Bedrooms))
        recent_rows.append(
            {
                "id": int(r.Id),
                "location": r.Location,
                "area": int(r.Area),
                "bedrooms": int(r.Bedrooms),
                "bathrooms": int(r.Bathrooms),
                "price_lakhs": round(float(r.Price) / 100_000.0, 2),
                "property_type": prop_label,
                "parking": r.Garage,
            }
        )

    similar = df.sample(n=min(4, len(df)), random_state=7)
    similar_props = []
    for r in similar.itertuples(index=False):
        similar_props.append(
            {
                "title": f"{int(r.Bedrooms)} BR near {r.Location}",
                "subtitle": f"{int(r.Area)} sq.ft · {r.Condition}",
                "price": _format_inr_lakhs(float(r.Price)),
            }
        )

    accuracy_pct = max(0.0, min(99.9, r2_test * 100))

    med_floors = int(df["Floors"].median())
    med_year = int(df["YearBuilt"].median())

    _CACHE = {
        "medians": {"floors": med_floors, "year_built": med_year},
        "kpi": {
            "total_houses": n,
            "avg_price_lakhs": round(avg_l, 2),
            "avg_price_label": _format_inr_lakhs(avg_l * 100_000),
            "max_price_label": _format_inr_lakhs(max_p),
            "min_price_label": _format_inr_lakhs(min_p),
            "model_accuracy": round(accuracy_pct, 1),
            "locations": len(locations),
        },
        "charts": {
            "scatter": scatter_pts,
            "scatter_corr": round(corr, 2),
            "scatter_line": line_pts,
            "bar_labels": locations,
            "bar_values": [round(v, 2) for v in loc_avg_lakhs],
            "trend_labels": trend_labels,
            "trend_values": [round(v, 2) for v in trend_values],
            "hist_labels": hist["labels"],
            "hist_counts": hist["counts"],
            "donut_labels": donut_labels,
            "donut_values": donut_values,
        },
        "table": recent_rows,
        "similar": similar_props,
        "form_options": {
            "locations": locations,
            "bedrooms": sorted(df["Bedrooms"].unique().astype(int).tolist()),
            "bathrooms": sorted(df["Bathrooms"].unique().astype(int).tolist()),
        },
    }
    _CSV_MTIME = mtime
    return _CACHE


def predict_price(
    area: float,
    bedrooms: int,
    bathrooms: int,
    location: str,
    garage: str,
    property_type_key: str,
) -> tuple[float, float]:
    """Return (predicted_price_raw, confidence_0_100) using held-out R² as confidence proxy."""
    global _MODEL_PIPELINE
    bundle = load_dashboard_bundle()
    if _MODEL_PIPELINE is None:
        raise RuntimeError("Model not trained")

    condition = _PROPERTY_TO_CONDITION.get(
        (property_type_key or "apartment").lower(), "Good"
    )
    med = bundle["medians"]

    row = pd.DataFrame(
        [
            {
                "Area": float(area),
                "Bedrooms": int(bedrooms),
                "Bathrooms": int(bathrooms),
                "Floors": med["floors"],
                "YearBuilt": med["year_built"],
                "Location": location.strip(),
                "Condition": condition,
                "Garage": "Yes" if garage.strip().lower() in ("yes", "y", "1", "true") else "No",
            }
        ]
    )
    pred = float(_MODEL_PIPELINE.predict(row)[0])
    conf = float(bundle["kpi"]["model_accuracy"])
    return pred, conf


def charts_json_str(bundle: dict) -> str:
    """JSON for embedding in HTML (Chart.js)."""
    return json.dumps(bundle["charts"], separators=(",", ":"))


def format_inr_full(price: float) -> str:
    return _format_inr_full(price)
