"""
app.py
-------
Flask web application for Rising Waters — Catchment Flood Susceptibility Assessment.
Integrates the approved XGBoost pipeline model (models/best_flood_model.pkl)
for catchment-level flood susceptibility evaluation while preserving legacy
seasonal flood risk prediction features.

Features:
1. Approved XGBoost pipeline (best_flood_model.pkl) using Region, Season,
   AnnualRainfall, SeasonalRainfall, and Temperature.
2. Strict input validation rejecting missing, non-numeric, infinite, and out-of-range values.
3. Catchment Flood Susceptibility Assessment interface displaying High/Low susceptibility,
   model-estimated score/confidence, and the mandated scientific limitation disclaimer.
4. Automatic SQLite persistence (flood_history.db) with backward-compatible schema.
5. Interactive Analytics Dashboard with susceptibility breakdowns and regional/seasonal metrics.
6. Complete Prediction History table with clearing functionality.
7. CSV export of prediction history.
"""

import json
import logging
import math
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import joblib
import pandas as pd
from flask import Flask, Response, jsonify, redirect, render_template, request, url_for

import os

from db import (
    DEFAULT_DB_PATH,
    clear_all_predictions,
    generate_predictions_csv,
    get_all_predictions,
    get_current_kolkata_time,
    get_prediction_stats,
    init_db,
    save_prediction,
)

app = Flask(__name__)
app.config.setdefault("DATABASE", DEFAULT_DB_PATH)
app.config.setdefault("SECRET_KEY", os.environ.get("SECRET_KEY", "rising-waters-susceptibility-secure-key-2026"))

logger = logging.getLogger(__name__)

MODELS_DIR = Path("models")
LEGACY_MODEL_PATH = MODELS_DIR / "flood_model.pkl"
SCALER_PATH = MODELS_DIR / "scaler.pkl"
COLUMNS_PATH = MODELS_DIR / "model_columns.pkl"
NUMERIC_COLUMNS_PATH = MODELS_DIR / "numeric_columns.pkl"
METADATA_PATH = MODELS_DIR / "model_metadata.json"
SUSCEPTIBILITY_MODEL_PATH = MODELS_DIR / "best_flood_model.pkl"

# Valid categories matching OneHotEncoder in best_flood_model.pkl
VALID_REGIONS = ["Central", "East", "North", "South", "West"]
VALID_SEASONS = ["Monsoon", "Post-Monsoon", "Summer", "Winter"]

SCIENTIFIC_LIMITATION_DISCLAIMER = (
    "This system assesses baseline macro-hydrological catchment flood susceptibility "
    "using historical CWC and INDOFLOODS observations and long-term climatological indicators. "
    "It does not forecast imminent floods or provide real-time evacuation warnings. "
    "Real-time flood warnings require live rainfall forecasts, river-gauge telemetry, "
    "and official advisories from relevant authorities."
)


legacy_model = None
scaler = None
model_columns = None
numeric_columns = None
metadata = {}
susceptibility_model = None


def load_artifacts():
    global legacy_model, scaler, model_columns, numeric_columns, metadata, susceptibility_model
    # Load legacy Decision Tree model artifacts
    if LEGACY_MODEL_PATH.exists():
        legacy_model = joblib.load(LEGACY_MODEL_PATH)
        scaler = joblib.load(SCALER_PATH)
        model_columns = joblib.load(COLUMNS_PATH)
        numeric_columns = joblib.load(NUMERIC_COLUMNS_PATH)
        if METADATA_PATH.exists():
            with open(METADATA_PATH) as f:
                metadata = json.load(f)
    else:
        legacy_model = None

    # Load approved XGBoost Susceptibility Pipeline
    if SUSCEPTIBILITY_MODEL_PATH.exists():
        susceptibility_model = joblib.load(SUSCEPTIBILITY_MODEL_PATH)
        logger.info("Loaded XGBoost susceptibility pipeline from %s", SUSCEPTIBILITY_MODEL_PATH)
    else:
        susceptibility_model = None
        logger.warning("XGBoost susceptibility model not found at %s", SUSCEPTIBILITY_MODEL_PATH)


load_artifacts()
init_db(app.config.get("DATABASE", DEFAULT_DB_PATH))


def validate_susceptibility_inputs(form: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Validate submitted inputs for Catchment Flood Susceptibility Assessment.
    Returns (cleaned_dict, error_message).
    """
    # 1. Region
    region = form.get("region", "").strip()
    if not region:
        return None, "Region is required. Please select a valid Region."
    if region not in VALID_REGIONS:
        return None, f"Invalid Region '{region}'. Must be one of: {', '.join(VALID_REGIONS)}."

    # 2. Season
    season = form.get("season", "").strip()
    if not season:
        return None, "Season is required. Please select a valid Season."
    if season not in VALID_SEASONS:
        return None, f"Invalid Season '{season}'. Must be one of: {', '.join(VALID_SEASONS)}."

    # 3. AnnualRainfall
    raw_annual = form.get("annual_rainfall")
    if raw_annual is None or str(raw_annual).strip() == "":
        return None, "Annual Rainfall (mm) is required."
    try:
        annual_rainfall = float(raw_annual)
    except (ValueError, TypeError):
        return None, f"Invalid Annual Rainfall '{raw_annual}'. Must be a valid numerical value."
    if math.isnan(annual_rainfall) or math.isinf(annual_rainfall):
        return None, "Annual Rainfall must be a finite numerical value."
    if annual_rainfall < 0.0:
        return None, "Annual Rainfall cannot be negative."
    if annual_rainfall > 15000.0:
        return None, "Annual Rainfall exceeds physically realistic meteorological limits (0–15,000 mm)."

    # 4. SeasonalRainfall
    raw_seasonal = form.get("seasonal_rainfall")
    if raw_seasonal is None or str(raw_seasonal).strip() == "":
        return None, "Seasonal Rainfall (mm) is required."
    try:
        seasonal_rainfall = float(raw_seasonal)
    except (ValueError, TypeError):
        return None, f"Invalid Seasonal Rainfall '{raw_seasonal}'. Must be a valid numerical value."
    if math.isnan(seasonal_rainfall) or math.isinf(seasonal_rainfall):
        return None, "Seasonal Rainfall must be a finite numerical value."
    if seasonal_rainfall < 0.0:
        return None, "Seasonal Rainfall cannot be negative."
    if seasonal_rainfall > 12000.0:
        return None, "Seasonal Rainfall exceeds physically realistic meteorological limits (0–12,000 mm)."
    if seasonal_rainfall > annual_rainfall:
        return None, (
            f"Physical inconsistency: Seasonal rainfall ({seasonal_rainfall:.1f} mm) cannot "
            f"exceed total annual rainfall ({annual_rainfall:.1f} mm)."
        )

    # 5. Temperature
    raw_temp = form.get("temperature")
    if raw_temp is None or str(raw_temp).strip() == "":
        return None, "Temperature (°C) is required."
    try:
        temperature = float(raw_temp)
    except (ValueError, TypeError):
        return None, f"Invalid Temperature '{raw_temp}'. Must be a valid numerical value."
    if math.isnan(temperature) or math.isinf(temperature):
        return None, "Temperature must be a finite numerical value."
    if temperature < -50.0 or temperature > 60.0:
        return None, f"Temperature ({temperature:.1f} °C) is outside realistic terrestrial limits (-50°C to 60°C)."

    cleaned = {
        "region": region,
        "season": season,
        "annual_rainfall": round(annual_rainfall, 2),
        "seasonal_rainfall": round(seasonal_rainfall, 2),
        "temperature": round(temperature, 2),
    }
    return cleaned, None


def build_legacy_feature_row(form):
    """Turn the submitted seasonal rainfall readings into a single-row
    DataFrame matching the exact column layout the legacy model was trained on."""
    winter = float(form.get("winter_rainfall", 0))
    pre_monsoon = float(form.get("pre_monsoon_rainfall", 0))
    monsoon = float(form.get("monsoon_rainfall", 0))
    post_monsoon = float(form.get("post_monsoon_rainfall", 0))
    annual = winter + pre_monsoon + monsoon + post_monsoon

    raw = {
        "AnnualRainfall": annual,
        "WinterRainfall": winter,
        "PreMonsoonRainfall": pre_monsoon,
        "MonsoonRainfall": monsoon,
        "PostMonsoonRainfall": post_monsoon,
    }

    df = pd.DataFrame([raw])
    df = df[model_columns]
    df[numeric_columns] = scaler.transform(df[numeric_columns])
    return df, annual, winter, pre_monsoon, monsoon, post_monsoon


@app.route("/")
def index():
    return render_template(
        "index.html",
        model_ready=(susceptibility_model is not None or legacy_model is not None),
        susceptibility_ready=(susceptibility_model is not None),
        best_model_name="XGBoost Catchment Susceptibility Model" if susceptibility_model else metadata.get("best_model"),
        accuracy_by_model=metadata.get("accuracy_by_model", {}),
        regions=VALID_REGIONS,
        seasons=VALID_SEASONS,
        disclaimer=SCIENTIFIC_LIMITATION_DISCLAIMER,
        active_page="home",
    )


@app.route("/assess-susceptibility", methods=["POST"])
def assess_susceptibility():
    """Execute Catchment Flood Susceptibility Assessment using the approved XGBoost pipeline."""
    if susceptibility_model is None:
        return (
            render_template(
                "result.html",
                error="Approved susceptibility model ('best_flood_model.pkl') is not loaded.",
                active_page="home",
                disclaimer=SCIENTIFIC_LIMITATION_DISCLAIMER,
            ),
            500,
        )

    cleaned_data, error_msg = validate_susceptibility_inputs(request.form)
    if error_msg:
        return (
            render_template(
                "result.html",
                error=error_msg,
                active_page="home",
                disclaimer=SCIENTIFIC_LIMITATION_DISCLAIMER,
            ),
            400,
        )

    region = cleaned_data["region"]
    season = cleaned_data["season"]
    annual_rainfall = cleaned_data["annual_rainfall"]
    seasonal_rainfall = cleaned_data["seasonal_rainfall"]
    temperature = cleaned_data["temperature"]

    # Build DataFrame matching the exact pipeline feature names
    input_df = pd.DataFrame(
        [
            {
                "Region": region,
                "Season": season,
                "AnnualRainfall": annual_rainfall,
                "SeasonalRainfall": seasonal_rainfall,
                "Temperature": temperature,
            }
        ]
    )

    try:
        prediction = int(susceptibility_model.predict(input_df)[0])

        if hasattr(susceptibility_model, "predict_proba"):
            proba = susceptibility_model.predict_proba(input_df)[0]
            confidence = float(proba[prediction]) * 100.0
            flood_susceptibility_score = float(proba[1]) * 100.0
        else:
            confidence = None
            flood_susceptibility_score = None

        result_label = "High Flood Susceptibility" if prediction == 1 else "Low Flood Susceptibility"
        model_name = "XGBoost Catchment Susceptibility Model"

        # Scientific explanation of result
        if prediction == 1:
            explanation = (
                f"Catchment climatological indicators for {region} India during the {season} season "
                f"(Annual Rainfall: {annual_rainfall:.1f} mm, Seasonal Rainfall: {seasonal_rainfall:.1f} mm, "
                f"Temperature: {temperature:.1f} °C) indicate elevated macro-hydrological catchment flood susceptibility. "
                "Catchments with comparable precipitation volume and regional topography have historically shown "
                "heightened surface runoff accumulation and frequent hydrological gauge threshold exceedances."
            )
        else:
            explanation = (
                f"Catchment climatological indicators for {region} India during the {season} season "
                f"(Annual Rainfall: {annual_rainfall:.1f} mm, Seasonal Rainfall: {seasonal_rainfall:.1f} mm, "
                f"Temperature: {temperature:.1f} °C) indicate baseline low catchment flood susceptibility. "
                "Under these climatological conditions, historical hydrological observations show standard "
                "drainage capacity without widespread macro-scale catchment saturation."
            )

        # Automatically record susceptibility assessment to SQLite database
        try:
            save_prediction(
                annual=annual_rainfall,
                prediction_result=result_label,
                model_name=model_name,
                winter=0.0,
                pre_monsoon=0.0,
                monsoon=seasonal_rainfall if season == "Monsoon" else 0.0,
                post_monsoon=seasonal_rainfall if season == "Post-Monsoon" else 0.0,
                confidence=round(confidence, 2) if confidence is not None else None,
                region=region,
                season=season,
                seasonal_rainfall=seasonal_rainfall,
                temperature=temperature,
                assessment_type="Catchment Susceptibility",
                db_path=app.config.get("DATABASE", DEFAULT_DB_PATH),
            )
        except Exception as db_err:
            logger.error("Failed to save susceptibility assessment to database: %s", db_err)

        return render_template(
            "result.html",
            result=result_label,
            is_flood=(prediction == 1),
            confidence=round(confidence, 2) if confidence is not None else None,
            flood_score=round(flood_susceptibility_score, 2) if flood_susceptibility_score is not None else None,
            model_name=model_name,
            assessment_type="Catchment Flood Susceptibility Assessment",
            region=region,
            season=season,
            annual_rainfall=round(annual_rainfall, 1),
            seasonal_rainfall=round(seasonal_rainfall, 1),
            temperature=round(temperature, 1),
            explanation=explanation,
            disclaimer=SCIENTIFIC_LIMITATION_DISCLAIMER,
            active_page="home",
        )
    except Exception as exc:
        logger.exception("Susceptibility assessment failed")
        return (
            render_template(
                "result.html",
                error=f"Assessment failed: {exc}",
                active_page="home",
                disclaimer=SCIENTIFIC_LIMITATION_DISCLAIMER,
            ),
            500,
        )


@app.route("/predict", methods=["POST"])
def predict():
    """Predict route supporting both legacy seasonal rainfall inputs and
    new Catchment Flood Susceptibility Assessment inputs for 100% backward compatibility."""
    # Check if this is a Catchment Flood Susceptibility submission
    if "region" in request.form or "seasonal_rainfall" in request.form or "temperature" in request.form:
        return assess_susceptibility()

    # Legacy 4-season rainfall model execution
    if legacy_model is None:
        return render_template(
            "result.html",
            error="No trained model found. Run 'python train_model.py' first.",
            active_page="home",
            disclaimer=SCIENTIFIC_LIMITATION_DISCLAIMER,
        )

    try:
        (
            features,
            annual_rainfall,
            winter,
            pre_monsoon,
            monsoon,
            post_monsoon,
        ) = build_legacy_feature_row(request.form)

        prediction = int(legacy_model.predict(features)[0])

        if hasattr(legacy_model, "predict_proba"):
            confidence = float(legacy_model.predict_proba(features)[0][prediction]) * 100
        else:
            confidence = None

        result = "High Flood Risk" if prediction == 1 else "Low Flood Risk"
        model_name = metadata.get("best_model", "Decision Tree")

        # Automatically record legacy prediction to SQLite database
        try:
            save_prediction(
                winter=winter,
                pre_monsoon=pre_monsoon,
                monsoon=monsoon,
                post_monsoon=post_monsoon,
                annual=annual_rainfall,
                prediction_result=result,
                model_name=model_name,
                confidence=round(confidence, 2) if confidence is not None else None,
                assessment_type="Legacy Rainfall Risk",
                db_path=app.config.get("DATABASE", DEFAULT_DB_PATH),
            )
        except Exception as db_err:
            logger.error("Failed to save prediction to database: %s", db_err)

        return render_template(
            "result.html",
            result=result,
            is_flood=(prediction == 1),
            confidence=round(confidence, 2) if confidence is not None else None,
            model_name=model_name,
            assessment_type="Legacy Rainfall Risk Assessment",
            annual_rainfall=round(annual_rainfall, 1),
            winter_rainfall=round(winter, 1),
            pre_monsoon_rainfall=round(pre_monsoon, 1),
            monsoon_rainfall=round(monsoon, 1),
            post_monsoon_rainfall=round(post_monsoon, 1),
            disclaimer=SCIENTIFIC_LIMITATION_DISCLAIMER,
            active_page="home",
        )
    except Exception as exc:
        return render_template(
            "result.html",
            error=f"Prediction failed: {exc}",
            active_page="home",
            disclaimer=SCIENTIFIC_LIMITATION_DISCLAIMER,
        )


# Verified Stage 4.1 Evaluation Benchmark Metrics (from results/stage_4_1_model_comparison.csv)
STAGE_4_1_EVALUATION_METRICS = {
    "stratified": [
        {"model": "XGBoost (Approved)", "scope": "Known Catchments (Interpolation)", "accuracy": "88.92%", "precision": "85.83%", "recall": "93.24%", "f1": "89.38%", "roc_auc": "0.9571", "is_best": True},
        {"model": "Random Forest", "scope": "Known Catchments (Interpolation)", "accuracy": "88.42%", "precision": "85.21%", "recall": "92.99%", "f1": "88.93%", "roc_auc": "0.9555", "is_best": False},
        {"model": "KNN", "scope": "Known Catchments (Interpolation)", "accuracy": "88.36%", "precision": "85.93%", "recall": "91.74%", "f1": "88.74%", "roc_auc": "0.9410", "is_best": False},
        {"model": "Decision Tree", "scope": "Known Catchments (Interpolation)", "accuracy": "83.92%", "precision": "78.47%", "recall": "93.49%", "f1": "85.32%", "roc_auc": "0.8926", "is_best": False},
    ],
    "station_grouped": [
        {"model": "KNN", "scope": "Unseen Catchments (Spatial Generalization)", "accuracy": "65.44%", "precision": "72.77%", "recall": "47.78%", "f1": "56.57%", "roc_auc": "0.7437", "is_best": True},
        {"model": "Decision Tree", "scope": "Unseen Catchments (Spatial Generalization)", "accuracy": "63.29%", "precision": "69.38%", "recall": "46.16%", "f1": "54.14%", "roc_auc": "0.7590", "is_best": False},
        {"model": "XGBoost (Approved)", "scope": "Unseen Catchments (Spatial Generalization)", "accuracy": "60.25%", "precision": "67.73%", "recall": "33.92%", "f1": "43.90%", "roc_auc": "0.7842", "is_best": False},
        {"model": "Random Forest", "scope": "Unseen Catchments (Spatial Generalization)", "accuracy": "59.55%", "precision": "66.92%", "recall": "35.42%", "f1": "45.57%", "roc_auc": "0.7798", "is_best": False},
    ],
    "chronological": [
        {"model": "XGBoost (Prior-Calibrated Thresh=0.80)", "scope": "Future Decades (Prior Adjustment)", "accuracy": "55.56%", "precision": "28.69%", "recall": "87.05%", "f1": "43.16%", "roc_auc": "0.7090", "is_best": True},
        {"model": "KNN", "scope": "Future Decades (Prior Shift: 67% -> 19%)", "accuracy": "53.54%", "precision": "28.14%", "recall": "89.93%", "f1": "42.86%", "roc_auc": "0.7093", "is_best": False},
        {"model": "Decision Tree", "scope": "Future Decades (Prior Shift: 67% -> 19%)", "accuracy": "51.38%", "precision": "27.77%", "recall": "94.24%", "f1": "42.90%", "roc_auc": "0.6684", "is_best": False},
        {"model": "Random Forest", "scope": "Future Decades (Prior Shift: 67% -> 19%)", "accuracy": "51.13%", "precision": "27.50%", "recall": "92.99%", "f1": "42.45%", "roc_auc": "0.7658", "is_best": False},
        {"model": "XGBoost (Default Thresh=0.50)", "scope": "Future Decades (Prior Shift: 67% -> 19%)", "accuracy": "44.93%", "precision": "25.12%", "recall": "92.99%", "f1": "39.56%", "roc_auc": "0.7090", "is_best": False},
    ],
    "natural_stream": [
        {"model": "XGBoost (Natural Stream)", "scope": "Continuous CWC Stream (1.86% Floods)", "accuracy": "85.28%", "precision": "3.58%", "recall": "26.67%", "f1": "6.31%", "roc_auc": "0.6429", "is_best": True},
        {"model": "Decision Tree", "scope": "Natural Continuous Stream", "accuracy": "Not available", "precision": "Not available", "recall": "Not available", "f1": "Not available", "roc_auc": "Not available", "is_best": False},
        {"model": "Random Forest", "scope": "Natural Continuous Stream", "accuracy": "Not available", "precision": "Not available", "recall": "Not available", "f1": "Not available", "roc_auc": "Not available", "is_best": False},
        {"model": "KNN", "scope": "Natural Continuous Stream", "accuracy": "Not available", "precision": "Not available", "recall": "Not available", "f1": "Not available", "roc_auc": "Not available", "is_best": False},
    ],
}


@app.route("/dashboard")
def dashboard():
    stats = get_prediction_stats(app.config.get("DATABASE", DEFAULT_DB_PATH))
    return render_template(
        "dashboard.html",
        stats=stats,
        best_model_name="XGBoost Catchment Susceptibility Model" if susceptibility_model else metadata.get("best_model", "Decision Tree"),
        evaluation_metrics=STAGE_4_1_EVALUATION_METRICS,
        disclaimer=SCIENTIFIC_LIMITATION_DISCLAIMER,
        active_page="dashboard",
    )



@app.route("/history")
def history():
    predictions = get_all_predictions(app.config.get("DATABASE", DEFAULT_DB_PATH))
    cleared = request.args.get("cleared") == "true"
    return render_template(
        "history.html",
        predictions=predictions,
        cleared=cleared,
        active_page="history",
    )


@app.route("/history/clear", methods=["POST"])
def clear_history():
    clear_all_predictions(app.config.get("DATABASE", DEFAULT_DB_PATH))
    return redirect(url_for("history", cleared="true"))


@app.route("/history/export")
@app.route("/export-csv")
def export_csv():
    csv_data = generate_predictions_csv(app.config.get("DATABASE", DEFAULT_DB_PATH))
    filename = f"flood_predictions_history_{get_current_kolkata_time().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# =====================================================================
# REST API ENDPOINTS
# =====================================================================

@app.route("/api/health", methods=["GET"])
def api_health():
    """REST API health check and service metadata endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "Rising Waters – Catchment Flood Susceptibility Assessment API",
        "model_loaded": susceptibility_model is not None,
        "active_model": "XGBoost Catchment Susceptibility Model" if susceptibility_model else None,
        "input_features": ["Region", "Season", "AnnualRainfall", "SeasonalRainfall", "Temperature"],
        "valid_regions": VALID_REGIONS,
        "valid_seasons": VALID_SEASONS,
        "disclaimer": SCIENTIFIC_LIMITATION_DISCLAIMER,
    })


@app.route("/api/assess", methods=["POST"])
@app.route("/api/predict", methods=["POST"])
def api_assess():
    """JSON REST API endpoint for Catchment Flood Susceptibility Assessment."""
    if susceptibility_model is None:
        return jsonify({
            "status": "error",
            "message": "Approved susceptibility model ('best_flood_model.pkl') is not loaded.",
            "disclaimer": SCIENTIFIC_LIMITATION_DISCLAIMER,
        }), 500

    # Extract JSON or form payload
    if request.is_json:
        data = request.get_json(silent=True) or {}
    else:
        data = request.form.to_dict()

    # Normalize key names (handle camelCase, snake_case, PascalCase)
    normalized = {}
    for k, v in data.items():
        k_clean = str(k).lower().strip().replace(" ", "_").replace("-", "_")
        normalized[k_clean] = v

    # Support common key aliases
    if "annual_rainfall" not in normalized and "annualrainfall" in normalized:
        normalized["annual_rainfall"] = normalized["annualrainfall"]
    if "seasonal_rainfall" not in normalized and "seasonalrainfall" in normalized:
        normalized["seasonal_rainfall"] = normalized["seasonalrainfall"]

    cleaned_data, error_msg = validate_susceptibility_inputs(normalized)
    if error_msg:
        return jsonify({
            "status": "error",
            "message": error_msg,
            "disclaimer": SCIENTIFIC_LIMITATION_DISCLAIMER,
        }), 400

    region = cleaned_data["region"]
    season = cleaned_data["season"]
    annual_rainfall = cleaned_data["annual_rainfall"]
    seasonal_rainfall = cleaned_data["seasonal_rainfall"]
    temperature = cleaned_data["temperature"]

    input_df = pd.DataFrame([{
        "Region": region,
        "Season": season,
        "AnnualRainfall": annual_rainfall,
        "SeasonalRainfall": seasonal_rainfall,
        "Temperature": temperature,
    }])

    try:
        prediction = int(susceptibility_model.predict(input_df)[0])

        if hasattr(susceptibility_model, "predict_proba"):
            proba = susceptibility_model.predict_proba(input_df)[0]
            confidence = float(proba[prediction]) * 100.0
            flood_score = float(proba[1]) * 100.0
        else:
            confidence = None
            flood_score = None

        result_label = "High Flood Susceptibility" if prediction == 1 else "Low Flood Susceptibility"
        model_name = "XGBoost Catchment Susceptibility Model"

        if prediction == 1:
            explanation = (
                f"Catchment climatological indicators for {region} India during the {season} season "
                f"(Annual Rainfall: {annual_rainfall:.1f} mm, Seasonal Rainfall: {seasonal_rainfall:.1f} mm, "
                f"Temperature: {temperature:.1f} °C) indicate elevated macro-hydrological catchment flood susceptibility. "
                "Catchments with comparable precipitation volume and regional topography have historically shown "
                "heightened surface runoff accumulation and frequent hydrological gauge threshold exceedances."
            )
        else:
            explanation = (
                f"Catchment climatological indicators for {region} India during the {season} season "
                f"(Annual Rainfall: {annual_rainfall:.1f} mm, Seasonal Rainfall: {seasonal_rainfall:.1f} mm, "
                f"Temperature: {temperature:.1f} °C) indicate baseline low catchment flood susceptibility. "
                "Under these climatological conditions, historical hydrological observations show standard "
                "drainage capacity without widespread macro-scale catchment saturation."
            )

        # Record to SQLite database
        try:
            save_prediction(
                annual=annual_rainfall,
                prediction_result=result_label,
                model_name=model_name,
                winter=0.0,
                pre_monsoon=0.0,
                monsoon=seasonal_rainfall if season == "Monsoon" else 0.0,
                post_monsoon=seasonal_rainfall if season == "Post-Monsoon" else 0.0,
                confidence=round(confidence, 2) if confidence is not None else None,
                region=region,
                season=season,
                seasonal_rainfall=seasonal_rainfall,
                temperature=temperature,
                assessment_type="Catchment Susceptibility API",
                db_path=app.config.get("DATABASE", DEFAULT_DB_PATH),
            )
        except Exception as db_err:
            logger.error("Failed to save API assessment to database: %s", db_err)

        return jsonify({
            "status": "success",
            "prediction": prediction,
            "susceptibility_tier": result_label,
            "is_flood_susceptible": bool(prediction == 1),
            "confidence_score": round(confidence, 2) if confidence is not None else None,
            "flood_susceptibility_score": round(flood_score, 2) if flood_score is not None else None,
            "model_name": model_name,
            "assessment_type": "Catchment Flood Susceptibility Assessment",
            "inputs": {
                "region": region,
                "season": season,
                "annual_rainfall_mm": annual_rainfall,
                "seasonal_rainfall_mm": seasonal_rainfall,
                "temperature_c": temperature,
            },
            "explanation": explanation,
            "disclaimer": SCIENTIFIC_LIMITATION_DISCLAIMER,
        }), 200
    except Exception as exc:
        logger.exception("API susceptibility assessment failed")
        return jsonify({
            "status": "error",
            "message": f"Assessment failed: {exc}",
            "disclaimer": SCIENTIFIC_LIMITATION_DISCLAIMER,
        }), 500


if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_DEBUG", "True").lower() in ("true", "1")
    app.run(debug=debug_mode, host="127.0.0.1", port=5000)

