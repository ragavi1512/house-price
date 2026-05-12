"""Flask app for the house price prediction project."""

from functools import wraps

from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from dashboard_data import (
    CSV_PATH,
    charts_json_str,
    format_inr_full,
    load_dashboard_bundle,
    predict_price,
)

app = Flask(__name__)
app.secret_key = "change-me-for-production"

# Demo-only: move to environment variables or a user database for production.
VALID_LOGIN_EMAIL = "ragavipalani15122k@gmail.com"
VALID_LOGIN_PASSWORD = "Ragavi@15"


@app.context_processor
def inject_user():
    return {"current_user_email": session.get("user_email")}


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_email"):
            flash("Please log in to continue.", "error")
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/contact", methods=["POST"])
def contact():
    name = (request.form.get("name") or "").strip()
    email = (request.form.get("email") or "").strip()
    if not email:
        flash("Please enter your email so we can reply.", "error")
        return redirect(url_for("index") + "#contact")
    flash(f"Thanks{name and ', ' + name or ''} — we received your message.", "success")
    return redirect(url_for("index") + "#contact")


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_email"):
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = (request.form.get("email") or "").strip()
        password = request.form.get("password") or ""
        if email == VALID_LOGIN_EMAIL and password == VALID_LOGIN_PASSWORD:
            session["user_email"] = email
            flash("You are signed in.", "success")
            return redirect(url_for("dashboard"))
        flash("Invalid email or password.", "error")
        return redirect(url_for("login"))

    return render_template(
        "login.html",
        default_email=VALID_LOGIN_EMAIL,
        default_password=VALID_LOGIN_PASSWORD,
    )


@app.route("/dashboard")
@login_required
def dashboard():
    if not CSV_PATH.is_file():
        flash(
            f"Dataset missing: {CSV_PATH}. Add HPP.csv next to the project folder.",
            "error",
        )
        return redirect(url_for("index"))

    bundle = load_dashboard_bundle()
    charts_json = charts_json_str(bundle)
    return render_template(
        "dashboard.html",
        email=session["user_email"],
        bundle=bundle,
        charts_json=charts_json,
    )


@app.route("/analytics")
@login_required
def analytics():
    if not CSV_PATH.is_file():
        flash(
            f"Dataset missing: {CSV_PATH}. Add HPP.csv next to the project folder.",
            "error",
        )
        return redirect(url_for("index"))

    bundle = load_dashboard_bundle()
    charts_json = charts_json_str(bundle)
    return render_template(
        "analytics.html",
        email=session["user_email"],
        bundle=bundle,
        charts_json=charts_json,
    )


@app.route("/dataset")
@login_required
def dataset():
    if not CSV_PATH.is_file():
        flash(
            f"Dataset missing: {CSV_PATH}. Add HPP.csv next to the project folder.",
            "error",
        )
        return redirect(url_for("index"))

    bundle = load_dashboard_bundle()
    return render_template("dataset.html", email=session["user_email"], bundle=bundle)


@app.route("/location-analysis")
@login_required
def location_analysis():
    if not CSV_PATH.is_file():
        flash(
            f"Dataset missing: {CSV_PATH}. Add HPP.csv next to the project folder.",
            "error",
        )
        return redirect(url_for("index"))

    bundle = load_dashboard_bundle()
    charts_json = charts_json_str(bundle)
    return render_template(
        "location_analysis.html",
        email=session["user_email"],
        bundle=bundle,
        charts_json=charts_json,
    )


@app.route("/trends")
@login_required
def trends():
    if not CSV_PATH.is_file():
        flash(
            f"Dataset missing: {CSV_PATH}. Add HPP.csv next to the project folder.",
            "error",
        )
        return redirect(url_for("index"))

    bundle = load_dashboard_bundle()
    charts_json = charts_json_str(bundle)
    return render_template(
        "trends.html",
        email=session["user_email"],
        bundle=bundle,
        charts_json=charts_json,
    )


@app.route("/comparison")
@login_required
def comparison():
    if not CSV_PATH.is_file():
        flash(
            f"Dataset missing: {CSV_PATH}. Add HPP.csv next to the project folder.",
            "error",
        )
        return redirect(url_for("index"))

    bundle = load_dashboard_bundle()
    charts_json = charts_json_str(bundle)
    return render_template(
        "comparison.html",
        email=session["user_email"],
        bundle=bundle,
        charts_json=charts_json,
    )


@app.route("/reports")
@login_required
def reports():
    if not CSV_PATH.is_file():
        flash(
            f"Dataset missing: {CSV_PATH}. Add HPP.csv next to the project folder.",
            "error",
        )
        return redirect(url_for("index"))

    bundle = load_dashboard_bundle()
    return render_template("reports.html", email=session["user_email"], bundle=bundle)


@app.route("/settings")
@login_required
def settings():
    return render_template("settings.html", email=session["user_email"])


@app.route("/help")
@login_required
def help_support():
    return render_template("help.html", email=session["user_email"])


@app.route("/price-prediction")
@login_required
def price_prediction():
    if not CSV_PATH.is_file():
        flash(
            f"Dataset missing: {CSV_PATH}. Add HPP.csv next to the project folder.",
            "error",
        )
        return redirect(url_for("index"))

    bundle = load_dashboard_bundle()
    prediction = session.pop("last_prediction", None)
    return render_template(
        "price_prediction.html",
        email=session["user_email"],
        bundle=bundle,
        prediction=prediction,
    )


@app.route("/price-prediction/predict", methods=["POST"])
@login_required
def price_prediction_predict():
    if not CSV_PATH.is_file():
        flash("Dataset not found.", "error")
        return redirect(url_for("price_prediction"))

    try:
        area = float(request.form.get("area", 0))
        bedrooms = int(request.form.get("bedrooms", 0))
        bathrooms = int(request.form.get("bathrooms", 0))
    except (TypeError, ValueError):
        flash("Enter valid numbers for area, bedrooms, and bathrooms.", "error")
        return redirect(url_for("price_prediction"))

    location = (request.form.get("location") or "").strip()
    parking = (request.form.get("parking") or "No").strip()
    property_type = (request.form.get("property_type") or "apartment").strip()

    if area <= 0 or bedrooms <= 0 or bathrooms <= 0 or not location:
        flash("Please fill in area, bedrooms, bathrooms, and location.", "error")
        return redirect(url_for("price_prediction"))

    try:
        price, confidence = predict_price(
            area=area,
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            location=location,
            garage=parking,
            property_type_key=property_type,
        )
    except Exception as exc:  # noqa: BLE001
        flash(f"Prediction failed: {exc}", "error")
        return redirect(url_for("price_prediction"))

    bundle = load_dashboard_bundle()
    loc_means = dict(
        zip(bundle["charts"]["bar_labels"], bundle["charts"]["bar_values"])
    )
    loc_avg = float(loc_means.get(location, bundle["kpi"]["avg_price_lakhs"]))
    pred_lakhs = price / 100_000.0
    trend_pct = ((pred_lakhs - loc_avg) / loc_avg * 100) if loc_avg else 0.0

    session["last_prediction"] = {
        "price_full": format_inr_full(price),
        "price_lakhs": round(pred_lakhs, 2),
        "confidence": round(confidence, 1),
        "trend_pct": round(trend_pct, 1),
        "trend_up": trend_pct >= 0,
    }
    flash("Prediction updated from your inputs.", "success")
    return redirect(url_for("price_prediction"))


@app.route("/logout")
def logout():
    session.pop("user_email", None)
    flash("You have been signed out.", "info")
    return redirect(url_for("index"))


@app.route("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
