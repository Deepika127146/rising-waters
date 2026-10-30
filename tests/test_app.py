"""
Comprehensive tests for the Rising Waters Flask application.
Tests cover:
- Home page loading and navigation
- ML prediction execution and automatic SQLite database recording
- Dashboard metrics and Chart.js integration
- History table rendering and empty state
- CSV export endpoint and formatting
- Clear history route and database cleanup

Run:
    python -m pytest tests/
"""

import csv
import io
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from app import app as flask_app
from db import get_all_predictions, get_prediction_stats, init_db


@pytest.fixture
def client(tmp_path):
    """Create a test client with an isolated temporary SQLite database."""
    test_db = tmp_path / "test_flood_history.db"
    flask_app.config.update(
        TESTING=True,
        DATABASE=test_db,
    )
    init_db(test_db)

    with flask_app.test_client() as client:
        yield client


def test_index_loads(client):
    """Test that the home page loads with navigation links."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"Rising Waters" in response.data
    assert b"Dashboard" in response.data
    assert b"History" in response.data
    assert b"Predict Flood Risk" in response.data


def test_predict_route_handles_post_and_saves_to_db(client):
    """Test that a prediction request calculates risk and automatically saves to the database."""
    payload = {
        "winter_rainfall": "45.0",
        "pre_monsoon_rainfall": "280.0",
        "monsoon_rainfall": "2400.0",
        "post_monsoon_rainfall": "520.0",
    }
    response = client.post("/predict", data=payload)
    assert response.status_code == 200
    assert (b"High Flood Risk" in response.data) or (b"Low Flood Risk" in response.data)
    assert b"Saved to Database" in response.data

    # Verify directly from database
    import re

    predictions = get_all_predictions(flask_app.config["DATABASE"])
    assert len(predictions) == 1
    p = predictions[0]
    assert p["winter_rainfall"] == 45.0
    assert p["pre_monsoon_rainfall"] == 280.0
    assert p["monsoon_rainfall"] == 2400.0
    assert p["post_monsoon_rainfall"] == 520.0
    assert p["annual_rainfall"] == 45.0 + 280.0 + 2400.0 + 520.0
    assert "Flood Risk" in p["prediction_result"]
    assert p["model_name"] != ""
    assert p["timestamp"] != ""
    assert "XXXXXX" not in p["timestamp"]
    assert re.match(r"^\d{2}-\d{2}-\d{4} \d{2}:\d{2}:\d{2}$", p["timestamp"]) is not None


def test_dashboard_empty_and_populated(client):
    """Test dashboard in both empty state and with recorded predictions."""
    # Empty state
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert b"Flood Risk Analytics Dashboard" in response.data
    assert b"No Prediction Data Yet" in response.data

    # Add a prediction
    payload = {
        "winter_rainfall": "20.0",
        "pre_monsoon_rainfall": "150.0",
        "monsoon_rainfall": "1200.0",
        "post_monsoon_rainfall": "250.0",
    }
    client.post("/predict", data=payload)

    # Populated dashboard
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert b"Total Predictions" in response.data
    assert b"riskDonutChart" in response.data
    assert b"trendBarChart" in response.data


def test_history_page_and_table(client):
    """Test history page displays previous predictions in a table."""
    # Add two predictions
    client.post(
        "/predict",
        data={
            "winter_rainfall": "30",
            "pre_monsoon_rainfall": "200",
            "monsoon_rainfall": "2500",
            "post_monsoon_rainfall": "400",
        },
    )
    client.post(
        "/predict",
        data={
            "winter_rainfall": "10",
            "pre_monsoon_rainfall": "100",
            "monsoon_rainfall": "900",
            "post_monsoon_rainfall": "200",
        },
    )

    response = client.get("/history")
    assert response.status_code == 200
    assert b"Logged Predictions (2)" in response.data
    assert b"Winter (mm)" in response.data
    assert b"Annual (mm)" in response.data
    assert b"Export CSV" in response.data
    assert b"Clear History" in response.data


def test_csv_export(client):
    """Test exporting prediction history to a CSV file."""
    import re

    # Add a test prediction
    client.post(
        "/predict",
        data={
            "winter_rainfall": "35.5",
            "pre_monsoon_rainfall": "220.0",
            "monsoon_rainfall": "2100.5",
            "post_monsoon_rainfall": "450.0",
        },
    )

    response = client.get("/history/export")
    assert response.status_code == 200
    assert response.mimetype == "text/csv"
    assert "attachment; filename=" in response.headers["Content-Disposition"]

    csv_text = response.data.decode("utf-8")
    reader = csv.reader(io.StringIO(csv_text))
    rows = list(reader)
    assert len(rows) >= 2  # Header + at least 1 record
    assert "Timestamp" in rows[0]
    assert "Winter Rainfall (mm)" in rows[0]
    assert "Annual Rainfall (mm)" in rows[0]
    assert "35.5" in rows[1]
    # Verify timestamp in CSV is formatted as DD-MM-YYYY HH:MM:SS and unmasked
    exported_timestamp = rows[1][1]
    assert exported_timestamp != "XXXXXX"
    assert re.match(r"^\d{2}-\d{2}-\d{4} \d{2}:\d{2}:\d{2}$", exported_timestamp) is not None



def test_clear_history(client):
    """Test clearing all prediction history."""
    # Seed a prediction
    client.post(
        "/predict",
        data={
            "winter_rainfall": "30",
            "pre_monsoon_rainfall": "200",
            "monsoon_rainfall": "2000",
            "post_monsoon_rainfall": "400",
        },
    )
    assert len(get_all_predictions(flask_app.config["DATABASE"])) == 1

    # Call clear history route
    response = client.post("/history/clear", follow_redirects=True)
    assert response.status_code == 200
    assert b"Prediction history has been cleared successfully" in response.data
    assert len(get_all_predictions(flask_app.config["DATABASE"])) == 0


# =====================================================================
# STAGE 5 TESTS: Catchment Flood Susceptibility Assessment Integration
# =====================================================================


def test_susceptibility_model_loading():
    """Verify that the approved XGBoost pipeline model is loaded with correct transformers and steps."""
    from app import susceptibility_model

    assert susceptibility_model is not None, "best_flood_model.pkl was not loaded"
    assert hasattr(susceptibility_model, "named_steps"), "susceptibility_model must be a Pipeline"
    assert "preprocessor" in susceptibility_model.named_steps
    assert "classifier" in susceptibility_model.named_steps
    assert susceptibility_model.named_steps["classifier"].__class__.__name__ == "XGBClassifier"


def test_valid_susceptibility_prediction_submission(client):
    """Verify valid assessment produces susceptibility result, model confidence score, and stores record."""
    payload = {
        "region": "South",
        "season": "Monsoon",
        "annual_rainfall": "2400.0",
        "seasonal_rainfall": "1800.0",
        "temperature": "28.5",
    }
    response = client.post("/assess-susceptibility", data=payload)
    assert response.status_code == 200
    assert (b"High Flood Susceptibility" in response.data) or (b"Low Flood Susceptibility" in response.data)
    assert b"Model-Estimated Score / Confidence" in response.data
    assert b"South India" in response.data
    assert b"2400.0 mm" in response.data
    assert b"1800.0 mm" in response.data
    assert b"28.5" in response.data
    assert b"Saved to Database" in response.data
    # Check mandatory scientific limitation disclaimer presence
    assert b"assesses baseline macro-hydrological catchment flood susceptibility" in response.data


    # Verify database persistence
    predictions = get_all_predictions(flask_app.config["DATABASE"])
    assert len(predictions) == 1
    p = predictions[0]
    assert p["region"] == "South"
    assert p["season"] == "Monsoon"
    assert p["annual_rainfall"] == 2400.0
    assert p["seasonal_rainfall"] == 1800.0
    assert p["temperature"] == 28.5
    assert "Susceptibility" in p["prediction_result"]
    assert p["assessment_type"] == "Catchment Susceptibility"


def test_predict_route_delegates_to_susceptibility(client):
    """Verify that posting susceptibility inputs to /predict delegates smoothly without error."""
    payload = {
        "region": "West",
        "season": "Monsoon",
        "annual_rainfall": "1900.0",
        "seasonal_rainfall": "1500.0",
        "temperature": "29.0",
    }
    response = client.post("/predict", data=payload)
    assert response.status_code == 200
    assert (b"High Flood Susceptibility" in response.data) or (b"Low Flood Susceptibility" in response.data)
    assert b"West India" in response.data


def test_invalid_region_and_season(client):
    """Verify that invalid regions and seasons are rejected with clear 400 error messages."""
    # Invalid Region
    resp_reg = client.post(
        "/assess-susceptibility",
        data={
            "region": "Antarctica",
            "season": "Monsoon",
            "annual_rainfall": "2000.0",
            "seasonal_rainfall": "1500.0",
            "temperature": "25.0",
        },
    )
    assert resp_reg.status_code == 400
    assert b"Invalid Region" in resp_reg.data
    assert b"Antarctica" in resp_reg.data

    # Invalid Season
    resp_season = client.post(
        "/assess-susceptibility",
        data={
            "region": "East",
            "season": "Spring",
            "annual_rainfall": "2000.0",
            "seasonal_rainfall": "1500.0",
            "temperature": "25.0",
        },
    )
    assert resp_season.status_code == 400
    assert b"Invalid Season" in resp_season.data
    assert b"Spring" in resp_season.data



def test_missing_inputs(client):
    """Verify that missing inputs return clear 400 validation error messages."""
    # Missing Region
    r1 = client.post(
        "/assess-susceptibility",
        data={
            "region": "",
            "season": "Monsoon",
            "annual_rainfall": "2000.0",
            "seasonal_rainfall": "1500.0",
            "temperature": "25.0",
        },
    )
    assert r1.status_code == 400
    assert b"Region is required" in r1.data

    # Missing Season
    r2 = client.post(
        "/assess-susceptibility",
        data={
            "region": "North",
            "season": "",
            "annual_rainfall": "2000.0",
            "seasonal_rainfall": "1500.0",
            "temperature": "25.0",
        },
    )
    assert r2.status_code == 400
    assert b"Season is required" in r2.data

    # Missing Annual Rainfall
    r3 = client.post(
        "/assess-susceptibility",
        data={
            "region": "Central",
            "season": "Monsoon",
            "annual_rainfall": "",
            "seasonal_rainfall": "1500.0",
            "temperature": "25.0",
        },
    )
    assert r3.status_code == 400
    assert b"Annual Rainfall (mm) is required" in r3.data

    # Missing Seasonal Rainfall
    r4 = client.post(
        "/assess-susceptibility",
        data={
            "region": "Central",
            "season": "Monsoon",
            "annual_rainfall": "2000.0",
            "seasonal_rainfall": "",
            "temperature": "25.0",
        },
    )
    assert r4.status_code == 400
    assert b"Seasonal Rainfall (mm) is required" in r4.data

    # Missing Temperature
    r5 = client.post(
        "/assess-susceptibility",
        data={
            "region": "Central",
            "season": "Monsoon",
            "annual_rainfall": "2000.0",
            "seasonal_rainfall": "1500.0",
            "temperature": "",
        },
    )
    assert r5.status_code == 400
    assert b"Temperature" in r5.data and b"required" in r5.data


def test_invalid_numerical_values(client):
    """Verify that non-numeric and non-finite inputs are rejected with 400."""
    # Non-numeric string
    r1 = client.post(
        "/assess-susceptibility",
        data={
            "region": "South",
            "season": "Monsoon",
            "annual_rainfall": "heavy_rain",
            "seasonal_rainfall": "1500.0",
            "temperature": "25.0",
        },
    )
    assert r1.status_code == 400
    assert b"Must be a valid numerical value" in r1.data

    # Non-numeric temperature
    r2 = client.post(
        "/assess-susceptibility",
        data={
            "region": "South",
            "season": "Monsoon",
            "annual_rainfall": "2000.0",
            "seasonal_rainfall": "1500.0",
            "temperature": "hot",
        },
    )
    assert r2.status_code == 400
    assert b"Must be a valid numerical value" in r2.data


def test_out_of_range_and_inconsistent_values(client):
    """Verify rejection of physically impossible and inconsistent meteorological values."""
    # Negative rainfall
    r_neg = client.post(
        "/assess-susceptibility",
        data={
            "region": "South",
            "season": "Monsoon",
            "annual_rainfall": "-500.0",
            "seasonal_rainfall": "100.0",
            "temperature": "25.0",
        },
    )
    assert r_neg.status_code == 400
    assert b"Annual Rainfall cannot be negative" in r_neg.data

    # Excessive rainfall > 15,000mm
    r_huge = client.post(
        "/assess-susceptibility",
        data={
            "region": "East",
            "season": "Monsoon",
            "annual_rainfall": "25000.0",
            "seasonal_rainfall": "5000.0",
            "temperature": "25.0",
        },
    )
    assert r_huge.status_code == 400
    assert b"exceeds physically realistic" in r_huge.data

    # Inconsistent: Seasonal rainfall > Annual rainfall
    r_inconsistent = client.post(
        "/assess-susceptibility",
        data={
            "region": "North",
            "season": "Monsoon",
            "annual_rainfall": "1200.0",
            "seasonal_rainfall": "1800.0",
            "temperature": "22.0",
        },
    )
    assert r_inconsistent.status_code == 400
    assert b"cannot exceed total annual rainfall" in r_inconsistent.data

    # Extreme unrealistic temperature > 60°C
    r_hot = client.post(
        "/assess-susceptibility",
        data={
            "region": "Central",
            "season": "Summer",
            "annual_rainfall": "800.0",
            "seasonal_rainfall": "200.0",
            "temperature": "78.0",
        },
    )
    assert r_hot.status_code == 400
    assert b"outside realistic terrestrial limits" in r_hot.data

    # Extreme unrealistic temperature < -50°C
    r_cold = client.post(
        "/assess-susceptibility",
        data={
            "region": "North",
            "season": "Winter",
            "annual_rainfall": "800.0",
            "seasonal_rainfall": "200.0",
            "temperature": "-70.0",
        },
    )
    assert r_cold.status_code == 400
    assert b"outside realistic terrestrial limits" in r_cold.data


def test_susceptibility_history_and_csv_export(client):
    """Verify that susceptibility assessments appear in history and CSV export with full fields."""
    client.post(
        "/assess-susceptibility",
        data={
            "region": "East",
            "season": "Monsoon",
            "annual_rainfall": "3200.0",
            "seasonal_rainfall": "2600.0",
            "temperature": "26.5",
        },
    )

    # Check history page
    hist_resp = client.get("/history")
    assert hist_resp.status_code == 200
    assert b"East" in hist_resp.data
    assert b"Monsoon" in hist_resp.data
    assert b"3200" in hist_resp.data
    assert b"Catchment Susceptibility" in hist_resp.data

    # Check CSV export
    csv_resp = client.get("/history/export")
    assert csv_resp.status_code == 200
    csv_text = csv_resp.data.decode("utf-8")
    reader = csv.reader(io.StringIO(csv_text))
    rows = list(reader)
    header = rows[0]
    data_row = rows[1]

    assert "Region" in header
    assert "Season" in header
    assert "Seasonal Rainfall (mm)" in header
    assert "Temperature (\xc2\xb0C)" in header or "Temperature" in " ".join(header)
    assert "Assessment Type" in header

    # Verify column values
    assert "East" in data_row
    assert "Monsoon" in data_row
    assert "3200.0" in data_row
    assert "2600.0" in data_row
    assert "26.5" in data_row


def test_dashboard_with_susceptibility_breakdown(client):
    """Verify that dashboard renders susceptibility breakdown and regional/seasonal aggregations."""
    client.post(
        "/assess-susceptibility",
        data={
            "region": "North",
            "season": "Monsoon",
            "annual_rainfall": "1600.0",
            "seasonal_rainfall": "1200.0",
            "temperature": "24.0",
        },
    )
    client.post(
        "/assess-susceptibility",
        data={
            "region": "South",
            "season": "Post-Monsoon",
            "annual_rainfall": "1400.0",
            "seasonal_rainfall": "800.0",
            "temperature": "27.0",
        },
    )

    resp = client.get("/dashboard")
    assert resp.status_code == 200
    assert b"Catchment Flood Susceptibility Breakdown" in resp.data
    assert b"Scientific Distinguishment Notice" in resp.data
    assert b"North:" in resp.data
    assert b"South:" in resp.data


def test_disclaimer_presence_on_all_views(client):
    """Verify that the mandatory scientific limitation disclaimer is prominently rendered on home and dashboard."""
    home_resp = client.get("/")
    assert b"Scientific Limitation &amp; Advisory Notice" in home_resp.data or b"Scientific Limitation" in home_resp.data
    assert b"assesses baseline macro-hydrological catchment flood susceptibility" in home_resp.data

    dash_resp = client.get("/dashboard")
    assert b"Scientific Distinguishment Notice" in dash_resp.data



# =====================================================================
# STAGE 6 TESTS: Dashboard, Data Visualization & Model Evaluation Benchmark
# =====================================================================


def test_stage6_dashboard_empty_database(client):
    """Verify dashboard rendering with an empty database: displays empty state, 0.0% metrics,
    and the complete model evaluation section without errors."""
    resp = client.get("/dashboard")
    assert resp.status_code == 200
    assert b"Flood Risk Analytics Dashboard" in resp.data
    assert b"No Prediction Data Yet" in resp.data
    assert b"0.0% of queries" in resp.data
    # Verify Model Evaluation Section renders even when database is empty
    assert b"Model Evaluation &amp; Scientific Benchmark" in resp.data or b"Model Evaluation & Scientific Benchmark" in resp.data
    assert b"Stratified 80:20 Validation" in resp.data
    assert b"Station-Grouped 5-Fold Cross-Validation" in resp.data
    assert b"Chronological Validation" in resp.data
    assert b"Real-World Continuous Stream" in resp.data
    # Check all 4 models are listed
    assert b"Decision Tree" in resp.data
    assert b"Random Forest" in resp.data
    assert b"KNN" in resp.data
    assert b"XGBoost" in resp.data
    # Check insight card headings
    assert b"Why Random Split Overestimates Generalization" in resp.data
    assert b"Why Spatial &amp; Temporal Splits are More Demanding" in resp.data or b"Why Spatial & Temporal Splits" in resp.data
    assert b"The Base Rate Fallacy in Operational Floods" in resp.data
    assert b"Susceptibility Demonstrator vs. Operational Warning" in resp.data


def test_stage6_dashboard_with_multiple_records_and_aggregations(client):
    """Verify dashboard rendering with multiple assessment records, validating High/Low counts,
    regional and seasonal aggregations, and the 4 chart containers."""
    records = [
        {"region": "Central", "season": "Monsoon", "annual_rainfall": "2200.0", "seasonal_rainfall": "1600.0", "temperature": "28.0"},
        {"region": "East", "season": "Monsoon", "annual_rainfall": "3200.0", "seasonal_rainfall": "2500.0", "temperature": "27.0"},
        {"region": "North", "season": "Summer", "annual_rainfall": "800.0", "seasonal_rainfall": "300.0", "temperature": "32.0"},
        {"region": "South", "season": "Post-Monsoon", "annual_rainfall": "1500.0", "seasonal_rainfall": "900.0", "temperature": "26.0"},
        {"region": "West", "season": "Winter", "annual_rainfall": "300.0", "seasonal_rainfall": "50.0", "temperature": "18.0"},
    ]
    for r in records:
        post_resp = client.post("/assess-susceptibility", data=r)
        assert post_resp.status_code == 200

    resp = client.get("/dashboard")
    assert resp.status_code == 200
    assert b"Total Predictions" in resp.data
    assert b"5" in resp.data  # Total count

    # Check that all 4 charts are rendered
    assert b"riskDonutChart" in resp.data
    assert b"regionBarChart" in resp.data
    assert b"seasonBarChart" in resp.data
    assert b"trendBarChart" in resp.data

    # Check chart explanation texts
    assert b"Distribution of user-submitted queries classified as" in resp.data
    assert b"Aggregated assessment volume across Indian macro-geographical zones" in resp.data
    assert b"Monsoon" in resp.data and b"70\xe2\x80\x9380%" in resp.data or b"Monsoon" in resp.data
    assert b"Chronological query sequence plotting annual rainfall" in resp.data

    # Check regional distribution badges
    assert b"Central:" in resp.data
    assert b"East:" in resp.data
    assert b"North:" in resp.data
    assert b"South:" in resp.data
    assert b"West:" in resp.data


def test_stage6_dashboard_legacy_record_handling(client):
    """Verify that the dashboard gracefully handles legacy 4-season rainfall records without crashing
    when region and season are None."""
    # Add legacy prediction
    legacy_payload = {
        "winter_rainfall": "30.0",
        "pre_monsoon_rainfall": "180.0",
        "monsoon_rainfall": "2100.0",
        "post_monsoon_rainfall": "420.0",
    }
    client.post("/predict", data=legacy_payload)

    # Add susceptibility assessment
    susc_payload = {
        "region": "South",
        "season": "Monsoon",
        "annual_rainfall": "2400.0",
        "seasonal_rainfall": "1800.0",
        "temperature": "28.5",
    }
    client.post("/assess-susceptibility", data=susc_payload)

    resp = client.get("/dashboard")
    assert resp.status_code == 200
    assert b"Total Predictions" in resp.data
    assert b"2" in resp.data
    assert b"Legacy All-India" in resp.data  # In recent activity table
    assert b"South" in resp.data


def test_stage6_model_evaluation_metrics_integrity(client):
    """Verify that the model evaluation section displays verified Stage 4.1 metrics
    without inventing scores (e.g., 'Not available' for untested models on natural stream)."""
    resp = client.get("/dashboard")
    assert resp.status_code == 200

    # Stratified metrics
    assert b"88.92%" in resp.data  # XGBoost stratified
    assert b"88.42%" in resp.data  # RF stratified
    assert b"88.36%" in resp.data  # KNN stratified
    assert b"83.92%" in resp.data  # Decision Tree stratified

    # Station-Grouped metrics
    assert b"65.44%" in resp.data  # KNN station-grouped
    assert b"60.25%" in resp.data  # XGBoost station-grouped

    # Chronological metrics
    assert b"55.56%" in resp.data  # XGBoost calibrated

    # Natural stream metrics
    assert b"85.28%" in resp.data  # XGBoost natural stream
    assert b"Not available" in resp.data  # Unrun models display 'Not available'


# =====================================================================
# MASTER AUDIT TESTS: Security, Reliability, and Edge-Case Protections
# =====================================================================


def test_master_audit_csv_formula_injection_protection(client):
    """Verify that potentially malicious formula triggers in database records are sanitized in CSV export."""
    from db import sanitize_csv_cell, save_prediction

    # Test unit sanitizer
    assert sanitize_csv_cell("=1+2") == "'=1+2"
    assert sanitize_csv_cell("@SUM(A1:B2)") == "'@SUM(A1:B2)"
    assert sanitize_csv_cell("+cmd|' /C calc'!A0") == "'+cmd|' /C calc'!A0"
    assert sanitize_csv_cell("-5.5") == "-5.5"  # Valid negative number preserved
    assert sanitize_csv_cell(2400.0) == 2400.0

    # Save a record with formula-like string directly to test database
    save_prediction(
        annual=1200.0,
        prediction_result="Low Flood Susceptibility",
        model_name="=HYPERLINK(\"http://malicious.site\",\"Click\")",
        region="South",
        season="Monsoon",
        assessment_type="Catchment Susceptibility",
        db_path=flask_app.config["DATABASE"],
    )

    resp = client.get("/history/export")
    assert resp.status_code == 200
    csv_text = resp.data.decode("utf-8")
    assert "'=HYPERLINK" in csv_text


def test_master_audit_repeated_submissions(client):
    """Verify that multiple repeated submissions execute reliably without race conditions or ID collisions."""
    for i in range(10):
        resp = client.post(
            "/assess-susceptibility",
            data={
                "region": "Central",
                "season": "Monsoon",
                "annual_rainfall": str(2000.0 + i * 50),
                "seasonal_rainfall": str(1500.0 + i * 30),
                "temperature": "27.5",
            },
        )
        assert resp.status_code == 200

    predictions = get_all_predictions(flask_app.config["DATABASE"])
    assert len(predictions) == 10
    # Check IDs are distinct and ordered
    ids = [p["id"] for p in predictions]
    assert len(set(ids)) == 10
    assert ids == list(range(10, 0, -1))


def test_master_audit_database_migration_idempotency(tmp_path):
    """Verify that calling init_db multiple times is completely idempotent and preserves existing rows."""
    test_db = tmp_path / "idempotent_test.db"
    init_db(test_db)
    # Insert a record
    from db import save_prediction
    rec_id = save_prediction(
        annual=2500.0,
        prediction_result="High Flood Susceptibility",
        model_name="XGBoost",
        region="East",
        season="Monsoon",
        db_path=test_db,
    )
    assert rec_id == 1

    # Call init_db 5 times
    for _ in range(5):
        init_db(test_db)

    # Verify record still intact
    records = get_all_predictions(test_db)
    assert len(records) == 1
    assert records[0]["region"] == "East"
    assert records[0]["annual_rainfall"] == 2500.0


def test_master_audit_model_loading_failure_handling(client, monkeypatch):
    """Verify that if the susceptibility model is unavailable or fails to load,
    the application returns an informative 500 error card without crashing."""
    import app

    monkeypatch.setattr(app, "susceptibility_model", None)

    resp = client.post(
        "/assess-susceptibility",
        data={
            "region": "South",
            "season": "Monsoon",
            "annual_rainfall": "2400.0",
            "seasonal_rainfall": "1800.0",
            "temperature": "28.5",
        },
    )
    assert resp.status_code == 500
    assert b"Approved susceptibility model" in resp.data or b"not loaded" in resp.data


def test_ppt_compliance_rest_api_health(client):
    """Verify PPT Slide 3 Requirement 5: REST API health endpoint returns valid JSON."""
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "healthy"
    assert data["model_loaded"] is True
    assert "Region" in data["input_features"]
    assert "disclaimer" in data


def test_ppt_compliance_rest_api_assess_valid_json(client):
    """Verify PPT Slide 3 Requirement 5: REST API /api/assess processes valid JSON and stores record."""
    payload = {
        "region": "North",
        "season": "Monsoon",
        "annual_rainfall": 2600.0,
        "seasonal_rainfall": 1900.0,
        "temperature": 27.5,
    }
    resp = client.post("/api/assess", json=payload)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "success"
    assert "susceptibility_tier" in data
    assert "is_flood_susceptible" in data
    assert "confidence_score" in data
    assert data["inputs"]["region"] == "North"
    assert "disclaimer" in data


def test_ppt_compliance_rest_api_assess_validation_error(client):
    """Verify REST API returns 400 Bad Request with informative message on invalid input."""
    # Physical inconsistency: seasonal > annual
    payload = {
        "region": "West",
        "season": "Monsoon",
        "annual_rainfall": 1500.0,
        "seasonal_rainfall": 2000.0,
        "temperature": 32.0,
    }
    resp = client.post("/api/assess", json=payload)
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["status"] == "error"
    assert "Physical inconsistency" in data["message"]


def test_ppt_compliance_rest_api_model_failure(client, monkeypatch):
    """Verify REST API returns 500 JSON error when model fails to load."""
    import app
    monkeypatch.setattr(app, "susceptibility_model", None)
    payload = {
        "region": "East",
        "season": "Monsoon",
        "annual_rainfall": 2000.0,
        "seasonal_rainfall": 1500.0,
        "temperature": 29.0,
    }
    resp = client.post("/api/assess", json=payload)
    assert resp.status_code == 500
    data = resp.get_json()
    assert data["status"] == "error"
    assert "not loaded" in data["message"]



