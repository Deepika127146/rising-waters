"""
db.py
-----
SQLite database helper module for Rising Waters.
Handles automatic recording of flood predictions, history retrieval,
statistical aggregations for the dashboard, and CSV export.

Uses Asia/Kolkata timezone and formats timestamps as DD-MM-YYYY HH:MM:SS.
"""

import csv
import io
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Configure Asia/Kolkata timezone with robust fallbacks
try:
    from zoneinfo import ZoneInfo
    KOLKATA_TZ = ZoneInfo("Asia/Kolkata")
except Exception:
    try:
        import pytz
        KOLKATA_TZ = pytz.timezone("Asia/Kolkata")
    except Exception:
        KOLKATA_TZ = timezone(timedelta(hours=5, minutes=30))

DEFAULT_DB_PATH = Path(__file__).resolve().parent / "flood_history.db"


def get_current_kolkata_time() -> datetime:
    """Return the current datetime in Asia/Kolkata timezone."""
    return datetime.now(KOLKATA_TZ)


def format_timestamp(raw_timestamp: Any) -> str:
    """Format any timestamp string into the required readable format:
    DD-MM-YYYY HH:MM:SS without truncation or masking."""
    if not raw_timestamp or str(raw_timestamp).strip() in ("", "None", "XXXXXX"):
        return get_current_kolkata_time().strftime("%d-%m-%Y %H:%M:%S")

    ts_str = str(raw_timestamp).strip()

    # If already in DD-MM-YYYY HH:MM:SS format
    for fmt in (
        "%d-%m-%Y %H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%d/%m/%Y %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
    ):
        try:
            dt = datetime.strptime(ts_str, fmt)
            return dt.strftime("%d-%m-%Y %H:%M:%S")
        except ValueError:
            continue

    return ts_str


def get_db_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Create and return a SQLite database connection with row factory and WAL mode."""
    path = db_path or DEFAULT_DB_PATH
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
    except Exception:
        pass
    return conn


def sanitize_csv_cell(val: Any) -> Any:
    """Sanitize string values to prevent CSV formula injection in spreadsheet software.
    Prepends a single quote if string begins with =, +, -, or @ and is not a valid number."""
    if val is None:
        return ""
    val_str = str(val)
    if val_str and val_str[0] in ("=", "+", "-", "@"):
        try:
            float(val_str)
            return val
        except ValueError:
            return f"'{val_str}"
    return val



def init_db(db_path: Optional[Path] = None) -> None:
    """Initialize the predictions table and ensure existing timestamps
    are standardized to DD-MM-YYYY HH:MM:SS. Safely migrates schema to support
    Catchment Flood Susceptibility Assessment fields without data loss."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                winter_rainfall REAL DEFAULT 0.0,
                pre_monsoon_rainfall REAL DEFAULT 0.0,
                monsoon_rainfall REAL DEFAULT 0.0,
                post_monsoon_rainfall REAL DEFAULT 0.0,
                annual_rainfall REAL NOT NULL,
                prediction_result TEXT NOT NULL,
                model_name TEXT NOT NULL,
                confidence REAL,
                timestamp TEXT NOT NULL,
                region TEXT,
                season TEXT,
                seasonal_rainfall REAL,
                temperature REAL,
                assessment_type TEXT DEFAULT 'Catchment Susceptibility'
            );
            """
        )
        conn.commit()

        # Check existing table columns and add any missing columns safely
        cursor.execute("PRAGMA table_info(predictions)")
        existing_cols = {row["name"] for row in cursor.fetchall()}

        new_columns = [
            ("region", "TEXT"),
            ("season", "TEXT"),
            ("seasonal_rainfall", "REAL"),
            ("temperature", "REAL"),
            ("assessment_type", "TEXT DEFAULT 'Catchment Susceptibility'"),
        ]
        for col_name, col_type in new_columns:
            if col_name not in existing_cols:
                cursor.execute(f"ALTER TABLE predictions ADD COLUMN {col_name} {col_type}")
        conn.commit()

        # Update legacy records where region IS NULL to reflect Legacy Rainfall Risk
        cursor.execute(
            "UPDATE predictions SET assessment_type = 'Legacy Rainfall Risk' WHERE (region IS NULL OR region = '') AND assessment_type = 'Catchment Susceptibility'"
        )
        conn.commit()

        # Migrate existing timestamps if stored in ISO or YYYY-MM-DD format
        cursor.execute("SELECT id, timestamp FROM predictions")

        rows = cursor.fetchall()
        for row in rows:
            raw_ts = row["timestamp"]
            formatted_ts = format_timestamp(raw_ts)
            if formatted_ts != raw_ts:
                cursor.execute(
                    "UPDATE predictions SET timestamp = ? WHERE id = ?",
                    (formatted_ts, row["id"]),
                )
        conn.commit()


def save_prediction(
    winter: float = 0.0,
    pre_monsoon: float = 0.0,
    monsoon: float = 0.0,
    post_monsoon: float = 0.0,
    annual: float = 0.0,
    prediction_result: str = "",
    model_name: str = "",
    confidence: Optional[float] = None,
    timestamp: Optional[str] = None,
    region: Optional[str] = None,
    season: Optional[str] = None,
    seasonal_rainfall: Optional[float] = None,
    temperature: Optional[float] = None,
    assessment_type: str = "Catchment Susceptibility",
    db_path: Optional[Path] = None,
) -> int:
    """Save a prediction or susceptibility assessment record into the SQLite database.
    Timestamp is recorded in Asia/Kolkata timezone formatted as DD-MM-YYYY HH:MM:SS.
    Returns the inserted record ID.
    """
    init_db(db_path)
    if timestamp is None or str(timestamp).strip() in ("", "None", "XXXXXX"):
        timestamp = get_current_kolkata_time().strftime("%d-%m-%Y %H:%M:%S")
    else:
        timestamp = format_timestamp(timestamp)

    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO predictions (
                winter_rainfall,
                pre_monsoon_rainfall,
                monsoon_rainfall,
                post_monsoon_rainfall,
                annual_rainfall,
                prediction_result,
                model_name,
                confidence,
                timestamp,
                region,
                season,
                seasonal_rainfall,
                temperature,
                assessment_type
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                float(winter) if winter is not None else 0.0,
                float(pre_monsoon) if pre_monsoon is not None else 0.0,
                float(monsoon) if monsoon is not None else 0.0,
                float(post_monsoon) if post_monsoon is not None else 0.0,
                float(annual),
                str(prediction_result),
                str(model_name),
                float(confidence) if confidence is not None else None,
                str(timestamp),
                str(region) if region is not None else None,
                str(season) if season is not None else None,
                float(seasonal_rainfall) if seasonal_rainfall is not None else None,
                float(temperature) if temperature is not None else None,
                str(assessment_type),
            ),
        )
        conn.commit()
        return cursor.lastrowid


def get_all_predictions(db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Retrieve all prediction records ordered by latest first,
    ensuring timestamps are formatted as DD-MM-YYYY HH:MM:SS."""
    init_db(db_path)
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM predictions ORDER BY id DESC")
        rows = cursor.fetchall()
        result = []
        for row in rows:
            record = dict(row)
            record["timestamp"] = format_timestamp(record.get("timestamp"))
            result.append(record)
        return result


def get_prediction_stats(db_path: Optional[Path] = None) -> Dict[str, Any]:
    """Calculate aggregated metrics and distributions for the dashboard."""
    init_db(db_path)
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()

        # Total count
        cursor.execute("SELECT COUNT(*) AS total FROM predictions")
        total = cursor.fetchone()["total"]

        # High-risk / High-susceptibility count
        cursor.execute(
            "SELECT COUNT(*) AS high FROM predictions WHERE prediction_result LIKE '%High%'"
        )
        high_risk = cursor.fetchone()["high"]

        # Low-risk / Low-susceptibility count
        cursor.execute(
            "SELECT COUNT(*) AS low FROM predictions WHERE prediction_result LIKE '%Low%'"
        )
        low_risk = cursor.fetchone()["low"]

        # Average annual rainfall
        cursor.execute("SELECT AVG(annual_rainfall) AS avg_annual FROM predictions")
        avg_row = cursor.fetchone()
        avg_annual = round(avg_row["avg_annual"], 1) if avg_row and avg_row["avg_annual"] is not None else 0.0

        # High and Low Risk percentages
        high_pct = round((high_risk / total * 100), 1) if total > 0 else 0.0
        low_pct = round((low_risk / total * 100), 1) if total > 0 else 0.0

        # Susceptibility Assessments specifically
        cursor.execute(
            "SELECT COUNT(*) AS total_susc FROM predictions WHERE region IS NOT NULL OR assessment_type LIKE '%Susceptibility%'"
        )
        total_susc = cursor.fetchone()["total_susc"]

        cursor.execute(
            "SELECT COUNT(*) AS high_susc FROM predictions WHERE (region IS NOT NULL OR assessment_type LIKE '%Susceptibility%') AND prediction_result LIKE '%High%'"
        )
        high_susc = cursor.fetchone()["high_susc"]

        cursor.execute(
            "SELECT COUNT(*) AS low_susc FROM predictions WHERE (region IS NOT NULL OR assessment_type LIKE '%Susceptibility%') AND prediction_result LIKE '%Low%'"
        )
        low_susc = cursor.fetchone()["low_susc"]

        # Regional distribution
        cursor.execute(
            "SELECT region, COUNT(*) AS count FROM predictions WHERE region IS NOT NULL AND region != '' GROUP BY region"
        )
        regional_summary = {r["region"]: r["count"] for r in cursor.fetchall()}
        canonical_regions = ["Central", "East", "North", "South", "West"]
        regional_counts = {reg: regional_summary.get(reg, 0) for reg in canonical_regions}

        # Seasonal distribution
        cursor.execute(
            "SELECT season, COUNT(*) AS count FROM predictions WHERE season IS NOT NULL AND season != '' GROUP BY season"
        )
        seasonal_summary = {r["season"]: r["count"] for r in cursor.fetchall()}
        canonical_seasons = ["Monsoon", "Post-Monsoon", "Summer", "Winter"]
        seasonal_counts = {s: seasonal_summary.get(s, 0) for s in canonical_seasons}

        # Latest 5 predictions
        cursor.execute("SELECT * FROM predictions ORDER BY id DESC LIMIT 5")
        recent_rows = []
        for r in cursor.fetchall():
            rec = dict(r)
            rec["timestamp"] = format_timestamp(rec.get("timestamp"))
            recent_rows.append(rec)

        # Recent predictions for timeline / trend chart (ordered chronologically)
        cursor.execute("SELECT * FROM predictions ORDER BY id DESC LIMIT 15")
        trend_rows = []
        for r in cursor.fetchall():
            rec = dict(r)
            rec["timestamp"] = format_timestamp(rec.get("timestamp"))
            trend_rows.append(rec)
        trend_rows.reverse()

    return {
        "total_predictions": total,
        "high_risk_predictions": high_risk,
        "low_risk_predictions": low_risk,
        "high_risk_percentage": high_pct,
        "low_risk_percentage": low_pct,
        "avg_annual_rainfall": avg_annual,
        "total_susceptibility": total_susc,
        "high_susceptibility": high_susc,
        "low_susceptibility": low_susc,
        "regional_summary": regional_summary,
        "seasonal_summary": seasonal_summary,
        "regional_counts": regional_counts,
        "seasonal_counts": seasonal_counts,
        "recent_predictions": recent_rows,
        "trend_predictions": trend_rows,
    }



def clear_all_predictions(db_path: Optional[Path] = None) -> int:
    """Delete all records from the predictions table.

    Returns the count of deleted records.
    """
    init_db(db_path)
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) AS count FROM predictions")
        count = cursor.fetchone()["count"]
        cursor.execute("DELETE FROM predictions")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='predictions'")
        conn.commit()
        return count


def generate_predictions_csv(db_path: Optional[Path] = None) -> str:
    """Generate CSV string of all prediction records.
    Preserves complete, unmasked timestamps formatted as DD-MM-YYYY HH:MM:SS.
    Maintains backward compatibility with legacy columns while appending
    Catchment Susceptibility indicators."""
    predictions = get_all_predictions(db_path)
    output = io.StringIO()
    writer = csv.writer(output)

    # Header - keep existing column positions 0..9 intact for existing tests and tools!
    writer.writerow([
        "ID",
        "Timestamp",
        "Winter Rainfall (mm)",
        "Pre-Monsoon Rainfall (mm)",
        "Monsoon Rainfall (mm)",
        "Post-Monsoon Rainfall (mm)",
        "Annual Rainfall (mm)",
        "Predicted Risk",
        "Model Name",
        "Confidence (%)",
        "Region",
        "Season",
        "Seasonal Rainfall (mm)",
        "Temperature (°C)",
        "Assessment Type",
    ])

    for p in predictions:
        conf_str = f"{p['confidence']:.2f}" if p["confidence"] is not None else "N/A"
        timestamp_str = format_timestamp(p.get("timestamp"))
        writer.writerow([
            sanitize_csv_cell(p["id"]),
            sanitize_csv_cell(timestamp_str),
            sanitize_csv_cell(p["winter_rainfall"] if p.get("winter_rainfall") is not None else "0.0"),
            sanitize_csv_cell(p["pre_monsoon_rainfall"] if p.get("pre_monsoon_rainfall") is not None else "0.0"),
            sanitize_csv_cell(p["monsoon_rainfall"] if p.get("monsoon_rainfall") is not None else "0.0"),
            sanitize_csv_cell(p["post_monsoon_rainfall"] if p.get("post_monsoon_rainfall") is not None else "0.0"),
            sanitize_csv_cell(p["annual_rainfall"]),
            sanitize_csv_cell(p["prediction_result"]),
            sanitize_csv_cell(p["model_name"]),
            sanitize_csv_cell(conf_str),
            sanitize_csv_cell(p.get("region") or "N/A"),
            sanitize_csv_cell(p.get("season") or "N/A"),
            sanitize_csv_cell(p.get("seasonal_rainfall") if p.get("seasonal_rainfall") is not None else "N/A"),
            sanitize_csv_cell(p.get("temperature") if p.get("temperature") is not None else "N/A"),
            sanitize_csv_cell(p.get("assessment_type") or "Legacy Rainfall Risk"),
        ])

    return output.getvalue()


