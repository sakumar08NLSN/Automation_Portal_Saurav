from fastapi import FastAPI, APIRouter, UploadFile, File, HTTPException, Query, Form, Request, BackgroundTasks, Depends
from fastapi.responses import FileResponse, JSONResponse,StreamingResponse
import pandas as pd
import re 
import os
import json
import shutil
import time
import logging
import threading
import io
import csv
from contextlib import asynccontextmanager
from typing import Optional, List , Dict, Any
from C_data_processing import DataExplorer
import gc
from datetime import datetime, timedelta, timezone
from usa_audit_service import process_usa_audit_logic_stream
from mls_audit_service import process_mls_audit_logic_stream
from intl_audit_service import process_intl_audit_logic_stream
from japan_service  import process_japan_bsr
import traceback
import tempfile
import base64
import gspread


# 2. Add the SQLAlchemy Session
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from sqlalchemy import desc

# 3. Import your database connection and model
from database import get_db
from core.users.models import RoscoSubmission



from mm_bsa_checks import (
    duplicate_aid_final,
    audience_spotprice_check,
    program_category_check_mm,
    channel_country_mapping_check,
    apt_bt_check,
    season_monitoring_check,
    fixture_validation_check,
    stadium_consistency_check,
    event_quality_check,
    home_market_check,
    ps_content_check,
    ps_market_channel_check,
    ea_creation_check,
    mm_bsr_consistency_check,
    audience_spot_range_clean_view,
    previous_delivery_check,
    live_delayed_check,
    program_analysis_status_check,
)

from ops_mm_bsa_checks import (
    duplicate_aid_final,
    audience_spotprice_check,
    program_category_check_mm_ops,
    channel_country_mapping_check,
    apt_bt_check,
    season_monitoring_check,
    fixture_validation_check,
    stadium_consistency_check,
    event_quality_check,
    home_market_check,
    ps_content_check,
    ps_market_channel_check,
    ea_creation_check,
    mm_bsr_consistency_check,
    audience_spot_range_clean_view,
    previous_delivery_check,
    live_delayed_check,
    program_analysis_status_check,
)

logger = logging.getLogger("uvicorn.error")

# --- Import Tracker ---
try:
    from qc_tracker import QCAuditTracker
except ImportError:
    QCAuditTracker = None

# --- QC Specific Imports ---
from qc_checks import (
    detect_period_from_rosco,
    parse_frontend_dates,
    load_bsr,
    #new changes start
    auto_sort_bsr,
    period_check,
    completeness_check,
    overlap_duplicate_daybreak_check,
    program_category_check,
    check_event_matchday_competition,
    market_channel_consistency_check,
    rates_and_ratings_check,
    country_channel_id_check,
    #new changes start
    home_away_vs_phase_check,
    multiple_live_match_check,
    color_excel,
    generate_summary_sheet,
    metered_channel_estimation_check,
)



from C_data_processing_f1 import BSRValidator
from C_data_processing_EPL import EPLValidator
from C_data_processing_SerieA import SerieAValidator

# --- NEW QC IMPORTS ---
import qc_checks_1 as qc_general
import epl_checks 

# -------------------- ⚙️ Folder setup --------------------
BASE_DIR = os.getcwd()
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
OUTPUT_FOLDER = os.path.join(BASE_DIR, "outputs")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# -------------------- 🧹 Cleanup Functions --------------------
def cleanup_old_files(folder_path, max_age_minutes=30):
    now = time.time()
    max_age_seconds = max_age_minutes * 60
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if os.path.isfile(file_path):
            file_age = now - os.path.getmtime(file_path)
            if file_age > max_age_seconds:
                try:
                    os.remove(file_path)
                    print(f"🧹 Deleted old file: {file_path}")
                except Exception as e:
                    print(f"⚠️ Error deleting {file_path}: {e}")

def start_background_cleanup():
    def run_cleanup():
        while True:
            cleanup_old_files(UPLOAD_FOLDER, max_age_minutes=30)
            cleanup_old_files(OUTPUT_FOLDER, max_age_minutes=30)
            time.sleep(300)
    thread = threading.Thread(target=run_cleanup, daemon=True)
    thread.start()

start_background_cleanup()

# -------------------- 🚀 INITIALIZE ROUTER --------------------
# 💡 FIX: We use APIRouter here, not FastAPI()
qc_router = APIRouter()

# --- Helper Config Loader ---
def load_config():
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
        return config
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="config.json not found on server.")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="config.json is not valid JSON.")

def excel_date_to_num(dt):
    """
    Converts a datetime object to an Excel serial date number parts.
    Returns (integer_days, fractional_time).
    """
    if pd.isna(dt):
        return 0, 0
    # Excel's base date is December 30, 1899
    base_date = datetime(1899, 12, 30)
    delta = dt - base_date
    date_part = int(delta.days)
    # Fractional part of the day (e.g. 0.65625 for 15:45)
    time_part = (dt.hour * 3600 + dt.minute * 60 + dt.second) / 86400.0
    return date_part, time_part

def get_excel_serial_parts(dt):
    """
    Returns (integer_date_part, fractional_time_part) for Excel.
    Excel base date is Dec 30, 1899.
    """
    if pd.isna(dt):
        return 0, 0
    base_date = datetime(1899, 12, 30)
    delta = dt - base_date
    date_part = int(delta.days)
    time_part = (dt.hour * 3600 + dt.minute * 60 + dt.second) / 86400.0
    return date_part, time_part

def get_excel_serial_key(dt_val, tm_val):
    """
    Replicates Excel's =(CONCAT(Date, Time)*1)
    Excel base date is 1899-12-30.
    """
    try:
        dt = pd.to_datetime(dt_val)
        # Handle time which might be a string or a datetime object
        if isinstance(tm_val, str):
            tm = pd.to_datetime(tm_val)
        else:
            tm = tm_val
            
        # Excel Date Integer (Days since 1899-12-30)
        base_date = datetime(1899, 12, 30)
        delta_days = (dt - base_date).days
        
        # Excel Time Decimal (Fraction of 24 hours)
        time_fraction = (tm.hour * 3600 + tm.minute * 60 + tm.second) / 86400.0
        
        # Replicate CONCAT and *1 (which effectively sums them in Excel logic)
        # We round to 5 decimals to match Excel's typical precision for time
        serial_num = int(round(delta_days + time_fraction))
        return str(serial_num)
    except:
        return "0"
        
def clean_val(val):
    if pd.isna(val) or str(val).strip().upper() in ["#N/A", "#REF!", "NAN", "-", ""]:
        return 0.0
    s_val = str(val).replace('$', '').replace(',', '').strip()
    try:
        return float(s_val)
    except:
        return 0.0


# Helper to find header row dynamically
def find_header_row(df_raw, keyword):
    """Scans the first 20 rows of a dataframe to find a keyword and returns that index."""
    for i in range(min(20, len(df_raw))):
        row_str = df_raw.iloc[i].astype(str).str.upper().tolist()
        if any(keyword.upper() in s for s in row_str):
            return i
    return None

def resolve_column(df, *candidates):
    """
    Returns the first column that exists in df from candidates.
    Helps handle Date vs Date(UTC), Start vs Start(UTC), etc.
    """
    for c in candidates:
        if c in df.columns:
            return c
    return None

def resolve_column_rates(df_columns, *candidates):
    """Returns the actual column name from df_columns that matches any of the candidates."""
    # Create a lookup of normalized names to original names
    norm_map = {str(c).strip().upper(): c for c in df_columns}
    for cand in candidates:
        cand_norm = str(cand).strip().upper()
        if cand_norm in norm_map:
            return norm_map[cand_norm]
    return None

def clean_numeric(series):
    """Robustly converts series to float, handling strings with symbols or commas."""
    if series is None: return 0.0
    # If it's already numeric, just fillna and return
    if pd.api.types.is_numeric_dtype(series):
        return series.fillna(0.0)
    
    # Otherwise, clean string symbols
    cleaned = series.astype(str).str.replace(r'[^\d.]', '', regex=True)
    return pd.to_numeric(cleaned, errors='coerce').fillna(0.0)


# -------------------- 📂 Original API Endpoints --------------------

# 💡 NOTE: If you need app.state here, you must add 'request: Request' to parameters
# and access it via request.app.state.df

@qc_router.post("/api/upload_csv")
async def upload_csv(request: Request, file: UploadFile = File(...)):
    file_location = os.path.join(UPLOAD_FOLDER, file.filename) 
    try:
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Accessing state via request.app.state
        if hasattr(request.app.state, 'df'):
            request.app.state.df = pd.read_csv(file_location, index_col=0, parse_dates=True)

        return {"filename": file.filename, "detail": f"File successfully uploaded and saved to {file_location}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred during file upload: {e}")
    finally:
        await file.close()

# --------------------  End Points Using DataExplorer Class  --------------------

@qc_router.get("/api/summary")
async def read_summary_data(request: Request):
    if not hasattr(request.app.state, 'df') or request.app.state.df.empty:
        raise HTTPException(status_code=404, detail="Data not loaded. Upload Sales.csv first.")
    data = DataExplorer(request.app.state.df)
    return data.summary().json_response()

@qc_router.get("/api/kpis")
async def read_kpis(request: Request, country: str = Query(None)):
    if not hasattr(request.app.state, 'df') or request.app.state.df.empty:
        raise HTTPException(status_code=404, detail="Data not loaded. Upload Sales.csv first.")
    data = DataExplorer(request.app.state.df)
    return data.kpis(country)

@qc_router.get("/api/")
async def read_sales(request: Request, limit: int = Query(100, gt=0, lt=150000)):
    if not hasattr(request.app.state, 'df') or request.app.state.df.empty:
        raise HTTPException(status_code=404, detail="Data not loaded. Upload Sales.csv first.")
    data = DataExplorer(request.app.state.df, limit)
    return data.json_response()


# =========================
# FIX: SAFE COLUMN FLATTENER
# =========================
def _flatten(val):
    if isinstance(val, list):
        return val
    if isinstance(val, str):
        return [val]
    return []

# =========================
# FIX: FIXTURE EXTRACTOR
# =========================
def extract_fixtures_sheet(bsr_path):
    xl = pd.ExcelFile(bsr_path)
    for s in xl.sheet_names:
        if "fixture" in s.lower():
            return xl.parse(s)
    return None

# --------------------  QC API Endpoint --------------------

@qc_router.post("/run_qc")
def run_general_qc(
    rosco_file: UploadFile = File(...),
    bsr_file: UploadFile = File(...)
):
    """
    Streamlit-parity General QC with safe Metrics Tracking.
    """
    # 1. Initialize Tracker Safely
    tracker = QCAuditTracker(bsr_file.filename) if QCAuditTracker else None
    
    def log_step(name, dataframe, flag_col=None):
        if not tracker: return
        try:
            flagged = 0
            if dataframe is not None and flag_col and flag_col in dataframe.columns:
                flagged = (dataframe[flag_col].astype(str).str.upper() != 'OK').sum()
            
            tracker.log_check_result({
                "check_key": name,
                "status": "Completed",
                "details": {
                    "rows_processed": len(dataframe) if dataframe is not None else 0,
                    "rows_flagged": int(flagged)
                }
            })
        except Exception as e:
            print(f"Metrics Logging Error: {e}")

    config = load_config()
    col_map = config["column_mappings"]
    rules = config["qc_rules"]
    file_rules = config["file_rules"]

    rosco_path = os.path.join(UPLOAD_FOLDER, rosco_file.filename)
    bsr_path = os.path.join(UPLOAD_FOLDER, bsr_file.filename)

    try:
        # ---------------- Save files ----------------
        with open(rosco_path, "wb") as f:
            shutil.copyfileobj(rosco_file.file, f)
        with open(bsr_path, "wb") as f:
            shutil.copyfileobj(bsr_file.file, f)

        # ---------------- Period ----------------
        start_date, end_date = detect_period_from_rosco(rosco_path)

        # ---------------- Load BSR ----------------
        df = load_bsr(bsr_path)
        if tracker: tracker.stats["total_rows_processed"] = len(df)

        # ---------------- Resolve Columns ----------------
        bsr_cols = col_map["bsr"]
        bsr_cols["date"] = resolve_column(df, "Date", "Date(UTC)")
        bsr_cols["start_time"] = resolve_column(df, "Start", "Start(UTC)")
        bsr_cols["end_time"] = resolve_column(df, "End", "End(UTC)")

        missing = [k for k, v in bsr_cols.items() if v is None]
        if missing:
            raise HTTPException(status_code=400, detail=f"Missing required BSR columns: {missing}")

        # ---------------- AUTO SORT ----------------
        sort_cols = []
        for key in ("channel", "date", "start_time"):
            sort_cols.extend(_flatten(col_map["bsr"].get(key)))
        sort_cols = [c for c in sort_cols if c in df.columns]
        
        
        if sort_cols:
            df = df.sort_values(sort_cols).reset_index(drop=True)
        else:
            df = df.reset_index(drop=True)

        # ---------------- QC CHECKS ----------------
        df = period_check(df, start_date, end_date, col_map["bsr"])
        log_step("period_check", df)
        
        df = completeness_check(df, col_map["bsr"], rules.get("program_category", {}))
        log_step("completeness_check", df)

        df = overlap_duplicate_daybreak_check(df, col_map["bsr"], rules.get("overlap_check", {}))
        log_step("overlap_check", df, "QC_Overlap_Flag")
        
        df = program_category_check(bsr_path, df, col_map, rules.get("program_category", {}), file_rules)
        log_step("program_category_check", df)

        df = check_event_matchday_competition(df, bsr_path, col_map, file_rules)
        log_step("matchday_competition_check", df)

        df = market_channel_consistency_check(df, rosco_path, col_map, file_rules)
        log_step("consistency_check", df)

        df = rates_and_ratings_check(df, col_map["bsr"])
        log_step("rates_ratings_check", df)

        df = country_channel_id_check(df, col_map["bsr"])
        log_step("country_channel_id_check", df)

        # ---------------- OUTPUT ----------------
        output_file = f"QC_Result_{os.path.splitext(bsr_file.filename)[0]}.xlsx"
        output_path = os.path.join(OUTPUT_FOLDER, output_file)

        for c in df.select_dtypes(include=["datetimetz"]).columns:
            df[c] = df[c].dt.tz_localize(None)

        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="QC Results")

        color_excel(output_path, df)
        generate_summary_sheet(output_path, df, file_rules)

        # ---------------- FINALIZE TRACKER ----------------
        if tracker: tracker.finalize()

        return FileResponse(
            path=output_path,
            filename=output_file,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    except Exception as e:
        df = None
        gc.collect() 
        if tracker:
            tracker.log_check_result({"check_key": "general_qc_run", "status": "Failed"})
            tracker.finalize()
        
        for path in [rosco_path, bsr_path]:
            if path and os.path.exists(path):
                try: os.remove(path)
                except: pass
        raise HTTPException(status_code=500, detail=str(e))

# --- HELPERS FOR SANITIZATION ---
def get_safe_filename(filename: str) -> str:
    """Removes special characters to prevent Windows FileNotFoundError."""
    name_part = os.path.splitext(filename)[0]
    # Keep only alphanumeric, underscores, and hyphens
    safe_name = re.sub(r'[^\w\-_]', '_', name_part)
    return f"{safe_name}.xlsx"


@qc_router.post("/run_qc1")
def run_general_qc(
    rosco_file: UploadFile = File(...),
    bsr_file: UploadFile = File(...),
    live_tolerance_min: int = Form(60),
    highlight_tolerance_min: int = Form(0),
    start_date: str = Form(...), 
    end_date: str = Form(...),
    # --- NEW: Catch the 3 new fields from the React Frontend ---
    rosco_id: str = Form(""),       # Setting default to "" so it doesn't crash if empty
    destination_id: str = Form(""),
    user_name: str = Form(""),
    # -----------------------------------------------------------
    db: Session = Depends(get_db)
):
    """
    General QC Audit with Bulletproof Database Logging for ECS.
    Includes explicit User Inputs (Rosco ID, Destination, User Name).
    """
    t_start = time.time()
    logger.info(f"🚀 Starting QC for {bsr_file.filename} by User: {user_name}")

    abs_upload_folder = os.path.abspath(UPLOAD_FOLDER)
    abs_output_folder = os.path.abspath(OUTPUT_FOLDER)
    os.makedirs(abs_upload_folder, exist_ok=True)
    os.makedirs(abs_output_folder, exist_ok=True)

    config = load_config()
    col_map = config["column_mappings"]
    rules = config["qc_rules"]
    file_rules = config["file_rules"]
    
    rules.setdefault("program_category", {})
    rules["program_category"]["live_tolerance_min"] = live_tolerance_min
    rules["program_category"]["highlight_tolerance_min"] = highlight_tolerance_min

    rosco_path = os.path.join(abs_upload_folder, rosco_file.filename)
    bsr_path = os.path.join(abs_upload_folder, bsr_file.filename)

    try:
        with open(rosco_path, "wb") as f:
            shutil.copyfileobj(rosco_file.file, f)
        with open(bsr_path, "wb") as f:
            shutil.copyfileobj(bsr_file.file, f)
        
        parsed_start, parsed_end = parse_frontend_dates(start_date, end_date)
        
        # TAB VALIDATION
        bsr_xl = pd.ExcelFile(bsr_path)
        valid_keywords = ["worksheet" , "workbook", "database"]
        lower_sheets = [sheet.lower() for sheet in bsr_xl.sheet_names]
        has_valid_tab = any(any(kw in sheet for kw in valid_keywords) for sheet in lower_sheets)

        if not has_valid_tab:
            found_sheets = "\n• ".join(bsr_xl.sheet_names)
            error_msg = (
                f"Invalid File Structure: Missing Data Tab\n"
                f"The uploaded BSR file does not contain a recognized data sheet.\n\n"
                f"📍 Expected Tab Name:\n"
                f"• Must contain the word 'Workbook' or 'Database'\n\n"
                f"📑 Tabs found in your file:\n"
                f"• {found_sheets}\n\n"
                f"Please rename the main data tab in your Excel file and try again."
            )
            raise ValueError(error_msg)

        df = load_bsr(bsr_path)
        df.columns = df.columns.astype(str).str.replace("\xa0", " ", regex=False).str.strip()
        df.dropna(how='all', inplace=True)

        val_date_col = next((c for c in df.columns if c in ["Date (UTC/GMT)", "Date (UTC)", "BSR_UTC_Date", "Date"]), None)
        val_start_col = next((c for c in df.columns if c in ["Start (UTC)", "Start UTC", "Start", "Program Start (local)", "Start Time"]), None)
        market_col = next((c for c in df.columns if c in ["Market", "Country"]), None)
        channel_col = next((c for c in df.columns if c in ["TV-Channel", "TV Channel", "Broadcaster"]), None)

        cleanup_cols = [c for c in [market_col, val_date_col, channel_col] if c]
        if cleanup_cols:
            for c in cleanup_cols:
                df[c] = df[c].replace(r'^\s*$', pd.NA, regex=True)
            df.dropna(subset=cleanup_cols, how='all', inplace=True)

        if val_date_col and val_start_col:
            missing_data_df = df[df[val_date_col].isna() | df[val_start_col].isna()]
            if not missing_data_df.empty:
                bad_markets = missing_data_df[market_col].dropna().unique().tolist() if market_col else []
                bad_channels = missing_data_df[channel_col].dropna().unique().tolist() if channel_col else []
                error_msg = (
                    f"Data Validation Failed: Missing Dates or Times\n"
                    f"Found {len(missing_data_df)} row(s) missing essential '{val_date_col}' or '{val_start_col}' data.\n\n"
                    f"📍 Where to look in your Excel file:\n"
                    f"• Markets: {', '.join(bad_markets) if bad_markets else 'Unknown'}\n"
                    f"• Channels: {', '.join(bad_channels) if bad_channels else 'Unknown'}\n\n"
                    f"Please fill in the missing data for these rows and upload again."
                )
                raise ValueError(error_msg)

        df = auto_sort_bsr(df, col_map.get("bsr", {}))

        sort_cols = []
        for key in ("channel", "date", "start_time"):
            val = col_map["bsr"].get(key)
            if val:
                sort_cols.extend(_flatten(val))

        sort_cols = [c for c in sort_cols if c in df.columns]
        if sort_cols:
            for c in sort_cols:
                df[c] = df[c].astype(str)
            df = df.sort_values(sort_cols).reset_index(drop=True)

        # QC LOGIC
        df = period_check(df, parsed_start, parsed_end)
        df = completeness_check(df, col_map["bsr"], rules.get("program_category", {}))
        df = overlap_duplicate_daybreak_check(df, col_map["bsr"], rules.get("overlap_check", {}))
        df = program_category_check(bsr_path, df, col_map, rules.get("program_category", {}), file_rules)

        bsr_xl = pd.ExcelFile(bsr_path)
        fixture_keywords = ["fixture", "fixtures", "fixture list", "fixtures list"]
        fixture_sheet_name = next((s for s in bsr_xl.sheet_names if any(k in s.lower() for k in fixture_keywords)), None)
        
        fixtures_df = None
        if fixture_sheet_name:
            fixtures_df = bsr_xl.parse(fixture_sheet_name)
            df = check_event_matchday_competition(df, fixtures_df)
        else:
            df["Event_Matchday_Competition_OK"] = False
            df["Event_Matchday_Competition_Remark"] = "Fixtures sheet missing from BSR"
        
        df = market_channel_consistency_check(df, rosco_path, col_map, file_rules)
        df = rates_and_ratings_check(df, col_map["bsr"])
        df = country_channel_id_check(df, col_map["bsr"])
        df = home_away_vs_phase_check(df, col_map)
        df = multiple_live_match_check(df, col_map)
        df = metered_channel_estimation_check(df, col_map["bsr"], file_rules)
        
        safe_name = get_safe_filename(bsr_file.filename)
        output_file = f"QC_Result_{safe_name}"
        output_path = os.path.join(abs_output_folder, output_file)

        for c in df.select_dtypes(include=["datetimetz"]).columns:
            df[c] = df[c].dt.tz_localize(None)

        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="QC Results")
            if fixtures_df is not None:
                fixtures_df.to_excel(writer, index=False, sheet_name="Original Fixtures")

        color_excel(output_path, df)
        generate_summary_sheet(output_path, df)
        
        if not os.path.exists(output_path):
            raise FileNotFoundError(f"Final Excel file was not found at {output_path}")

        # =========================================================
        # 💡 BULLETPROOF DATABASE LOGGING BLOCK
        # =========================================================
        try:
            # 1. Extract Project ID (Auto from Filename)
            id_match = re.search(r"#(\d+)", rosco_file.filename)
            extracted_rosco_id = id_match.group(1) if id_match else "Unknown"

            # 2. Extract Project Name Safely
            project_name = "Unknown Project"
            try:
                rosco_xl = pd.ExcelFile(rosco_path)
                info_sheet = next((s for s in rosco_xl.sheet_names if "general" in s.lower() or "info" in s.lower()), None)
                if info_sheet:
                    info_df = rosco_xl.parse(info_sheet, header=None)
                    for idx, row in info_df.iterrows():
                        if "Events:" in str(row.iloc[0]):
                            project_name = str(row.iloc[1]).strip()
                            break
            except Exception as read_err:
                logger.warning(f"Could not read Rosco for project name: {read_err}")

            # 3. Calculate Summary & Errors
            summary_columns = [
                "Within_Period_OK", "Completeness_OK", "Duplicate_OK", 
                "Overlap_OK", "Daybreak_OK", "program_category_check_result", 
                "Event_Matchday_Competition_OK", "Market_Channel_Consistency_OK", 
                "Rates_Ratings_QC_OK", "Market_Channel_ID_OK", 
                "Home_vs_Away_vs_Phase_OK", "Multiple_Live_Match_OK", 
                "Metered_Estimation_Check_OK"
            ]

            qc_summary_dict = {}
            total_errors = 0

            for col in summary_columns:
                if col in df.columns:
                    valid_data = df[col].dropna()
                    str_data = valid_data.astype(str).str.upper().str.strip()
                    failed = int(str_data.isin(["FALSE", "FAILED", "0"]).sum())
                    passed = int(str_data.isin(["TRUE", "PASSED", "1", "OK"]).sum())
                    
                    total_eval = passed + failed
                    na_count = len(df) - total_eval
                    total_errors += failed

                    qc_summary_dict[col] = {
                        "Total_Evaluated": total_eval,
                        "Passed": passed,
                        "Failed": failed,
                        "NA": na_count
                    }

            run_duration = round(time.time() - t_start, 2)

            # 4. Save to Database (INCLUDING NEW USER INPUTS)
            new_rosco_record = RoscoSubmission(
                rosco_id=extracted_rosco_id,           # Auto-extracted
                project_name=project_name,             # Auto-extracted
                manual_rosco_id=rosco_id,              # User Input
                destination_id=destination_id,         # User Input
                user_name=user_name,                   # User Input
                run_duration=run_duration,
                error_count=total_errors,
                qc_summary=qc_summary_dict,
                original_filename=rosco_file.filename
            )
            db.add(new_rosco_record)
            db.commit()
            logger.info(f"✅ DB Log Saved: {project_name} | Errors: {total_errors} | User: {user_name}")

        except Exception as db_err:
            db.rollback() 
            logger.error(f"⚠️ Non-Fatal DB Error (File will still download): {str(db_err)}")
        # =========================================================

        logger.info(f"🏁 Sending file: {output_file}")
        return FileResponse(
            path=output_path,
            filename=output_file,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    except ValueError as ve:
        logger.warning(f"⚠️ Validation Error: {str(ve)}")
        raise HTTPException(status_code=400, detail=str(ve))
    
    except Exception as e:
        logger.error(f"❌ Error in run_qc1: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@qc_router.post("/run-mm-bsa-qc")
async def run_mm_bsa_qc(
    adapt_file: UploadFile = File(...),
    rosco_file: Optional[UploadFile] = File(None),   
    fixture_file: Optional[UploadFile] = File(None), 
    previous_delivery_file: Optional[UploadFile] = File(None),
    bsr_file: Optional[UploadFile] = File(None),
    selected_checks: str = Form(...),
    bt_threshold: Optional[float] = Form(None),
    start_date: Optional[str] = Form(None),
    end_date: Optional[str] = Form(None)
):
    try:
        print("\n🚀 ===== NEW REQUEST =====")

        # ---------------- PARSE CHECKS ----------------
        try:
            checks = json.loads(selected_checks)
        except:
            raise HTTPException(400, "Invalid selected_checks format")

        print("✅ Selected checks:", checks)

        # ---------------- SAVE FILES ----------------
        def save_file(file, prefix):
            if not file:
                return None
            path = os.path.join(UPLOAD_FOLDER, f"{prefix}{int(time.time())}{file.filename}")
            with open(path, "wb") as f:
                shutil.copyfileobj(file.file, f)
            return path

        adapt_path = save_file(adapt_file, "adapt")
        rosco_path = save_file(rosco_file, "rosco")
        fixture_path = save_file(fixture_file, "fixture")
        prev_path = save_file(previous_delivery_file, "prev")
        bsr_path = save_file(bsr_file, "bsr")

        print("📁 Files saved")

        # ---------------- LOAD ADAPT ----------------
        try:
            df = pd.read_excel(adapt_path, sheet_name="mm - detailed")
        except:
            df = pd.read_excel(adapt_path)

        df.columns = df.columns.str.strip()
        print("✅ Adapt loaded:", df.shape)

        # ---------------- LOAD OPTIONAL FILES ----------------
        fixture_df = None
        if fixture_path:
            fixture_df = pd.read_excel(fixture_path)
            fixture_df.columns = fixture_df.columns.str.strip()

        previous_delivery_df = None
        if prev_path:
            previous_delivery_df = pd.read_excel(prev_path)
            previous_delivery_df.columns = previous_delivery_df.columns.str.strip()

        bsr_df = None
        if bsr_path:
            try:
                bsr_df = pd.read_excel(bsr_path, sheet_name="Database", header=5)
            except:
                bsr_df = pd.read_excel(bsr_path, header=5)

            bsr_df.columns = bsr_df.columns.str.strip()

        # ---------------- RUN CHECKS ----------------
        print("⚙️ Running checks...")

        range_df = None
        prev_range_df = None

        if "duplicate_aid_final" in checks:
            df = duplicate_aid_final(df)

        if "audience_spotprice_check" in checks:
            df = audience_spotprice_check(df)

        if "program_category_check_mm" in checks:
            df = program_category_check_mm(df)

        if "ea_creation_check" in checks:
            df = ea_creation_check(df)

        if "channel_country_mapping_check" in checks:
            if not rosco_path:
                raise HTTPException(400, "ROSCO file required for channel mapping")
            df = channel_country_mapping_check(df, rosco_path)

        if "ps_market_channel_check" in checks or "ps_content_check" in checks:
            if not rosco_path:
                raise HTTPException(400, "ROSCO required")

            monitoring_df = pd.read_excel(rosco_path, sheet_name="Monitoring List")

            if "ps_market_channel_check" in checks:
                df = ps_market_channel_check(df, monitoring_df)

            if "ps_content_check" in checks:
                df = ps_content_check(df, monitoring_df)

        if "mm_bsr_consistency_check" in checks:
            if bsr_df is None:
                raise HTTPException(400, "BSR file required")
            df = mm_bsr_consistency_check(df, bsr_df)

        if "audience_spot_range_clean_view" in checks:
            range_df = audience_spot_range_clean_view(df)

        if "previous_delivery_check" in checks:
            if previous_delivery_df is None:
                raise HTTPException(400, "Previous delivery file required")
            prev_range_df = previous_delivery_check(df, previous_delivery_df)

        if "season_monitoring_check" in checks:
            if not start_date or not end_date:
                raise HTTPException(400, "Start and End date required")
            df = season_monitoring_check(df, start_date, end_date)

        if "fixture_validation_check" in checks:
            if fixture_df is None:
                raise HTTPException(400, "Fixture file required")
            df = fixture_validation_check(df, fixture_df)

        if "apt_bt_check" in checks:
            df = apt_bt_check(df, bt_threshold)

        if "stadium_consistency_check" in checks:
            df = stadium_consistency_check(df)

        if "event_quality_check" in checks:
            df = event_quality_check(df)

        if "home_market_check" in checks:
            df = home_market_check(df)

        print("✅ All checks completed")

        # ---------------- OUTPUT ----------------
        output_path = os.path.join(OUTPUT_FOLDER, f"MM_BSA_QC_{int(time.time())}.xlsx")

        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="MM_QC_Output", index=False)

            if range_df is not None and not range_df.empty:
                range_df.to_excel(writer, sheet_name="Audience_Range_Check", index=False)

            if prev_range_df is not None and not prev_range_df.empty:
                prev_range_df.to_excel(writer, sheet_name="Previous_Delivery_Check", index=False)

        print("📄 Output generated:", output_path)

        return FileResponse(
            output_path,
            filename="MM_BSA_QC_Output.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except HTTPException as e:
        print("❌ USER ERROR:", e.detail)
        raise e

    except Exception as e:
        traceback.print_exc()
        print("❌ SYSTEM ERROR:", str(e))
        return JSONResponse(
            status_code=500,
            content={"detail": f"Backend crashed: {str(e)}"}
        )

@qc_router.post("/run-mm-exclusive-qc")
async def run_mm_exclusive_qc(
    adapt_file: UploadFile = File(...),
    rosco_file: Optional[UploadFile] = File(None),   
    fixture_file: Optional[UploadFile] = File(None), 
    previous_delivery_file: Optional[UploadFile] = File(None),
    bsr_file: Optional[UploadFile] = File(None),
    selected_checks: str = Form(...),
    bt_threshold: Optional[float] = Form(None),
    start_date: Optional[str] = Form(None),
    end_date: Optional[str] = Form(None)
):
    try:
        print("\n🚀 ===== OPS MM EXCLUSIVE REQUEST =====")

        # ---------------- PARSE CHECKS ----------------
        try:
            checks = json.loads(selected_checks)
        except:
            raise HTTPException(400, "Invalid selected_checks format")

        print("✅ Selected checks:", checks)

        # ---------------- SAVE FILES ----------------
        def save_file(file, prefix):
            if not file:
                return None
            path = os.path.join(UPLOAD_FOLDER, f"{prefix}{int(time.time())}{file.filename}")
            with open(path, "wb") as f:
                shutil.copyfileobj(file.file, f)
            return path

        adapt_path = save_file(adapt_file, "adapt")
        rosco_path = save_file(rosco_file, "rosco")
        fixture_path = save_file(fixture_file, "fixture")
        prev_path = save_file(previous_delivery_file, "prev")
        bsr_path = save_file(bsr_file, "bsr")

        print("📁 Files saved")

        # ---------------- LOAD MAIN FILE ----------------
        try:
            df = pd.read_excel(adapt_path, sheet_name="mm - detailed")
        except:
            df = pd.read_excel(adapt_path)

        df.columns = df.columns.str.strip()
        print("✅ DPMM loaded:", df.shape)

        # ---------------- OPTIONAL FILES ----------------
        fixture_df = pd.read_excel(fixture_path) if fixture_path else None
        previous_delivery_df = pd.read_excel(prev_path) if prev_path else None

        bsr_df = None
        if bsr_path:
            try:
                bsr_df = pd.read_excel(bsr_path, sheet_name="Database", header=5)
            except:
                bsr_df = pd.read_excel(bsr_path, header=5)

        # ---------------- RUN CHECKS ----------------
        print("⚙️ Running OPS checks...")

        range_df = None
        prev_range_df = None

        if "duplicate_aid_final" in checks:
            df = duplicate_aid_final(df)

        if "audience_spotprice_check" in checks:
            df = audience_spotprice_check(df)

        # ✅ NOW SAME AS MM-BSA
        if "program_category_check_mm_ops" in checks:
            df = program_category_check_mm_ops(df)

        if "ea_creation_check" in checks:
            df = ea_creation_check(df)

        if "channel_country_mapping_check" in checks:
            if not rosco_path:
                raise HTTPException(400, "ROSCO required")
            df = channel_country_mapping_check(df, rosco_path)

        if "ps_market_channel_check" in checks or "ps_content_check" in checks:
            if not rosco_path:
                raise HTTPException(400, "ROSCO required")

            monitoring_df = pd.read_excel(rosco_path, sheet_name="Monitoring List")

            if "ps_market_channel_check" in checks:
                df = ps_market_channel_check(df, monitoring_df)

            if "ps_content_check" in checks:
                df = ps_content_check(df, monitoring_df)

        if "mm_bsr_consistency_check" in checks:
            if bsr_df is None:
                raise HTTPException(400, "BSR file required")
            df = mm_bsr_consistency_check(df, bsr_df)

        if "audience_spot_range_clean_view" in checks:
            range_df = audience_spot_range_clean_view(df)

        if "previous_delivery_check" in checks:
            if previous_delivery_df is None:
                raise HTTPException(400, "Previous delivery required")
            prev_range_df = previous_delivery_check(df, previous_delivery_df)

        if "season_monitoring_check" in checks:
            if not start_date or not end_date:
                raise HTTPException(400, "Start & End date required")
            df = season_monitoring_check(df, start_date, end_date)

        if "fixture_validation_check" in checks:
            if fixture_df is None:
                raise HTTPException(400, "Fixture required")
            df = fixture_validation_check(df, fixture_df)

        if "apt_bt_check" in checks:
            df = apt_bt_check(df, bt_threshold)

        if "stadium_consistency_check" in checks:
            df = stadium_consistency_check(df)

        if "event_quality_check" in checks:
            df = event_quality_check(df)

        if "home_market_check" in checks:
            df = home_market_check(df)

        if "live_delayed_check" in checks:
            df = live_delayed_check(df)

        if "program_analysis_status_check" in checks:
            df = program_analysis_status_check(df)

        print("✅ OPS checks completed")

        # ---------------- OUTPUT ----------------
        output_path = os.path.join(
            OUTPUT_FOLDER,
            f"OPS_MM_QC_{int(time.time())}.xlsx"
        )

        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="OPS_QC_Output", index=False)

            if range_df is not None and not range_df.empty:
                range_df.to_excel(writer, sheet_name="Audience_Range", index=False)

            if prev_range_df is not None and not prev_range_df.empty:
                prev_range_df.to_excel(writer, sheet_name="Previous_Delivery", index=False)

        print("📄 OPS Output generated:", output_path)

        return FileResponse(
            output_path,
            filename="OPS_MM_QC_Output.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except HTTPException as e:
        print("❌ USER ERROR:", e.detail)
        raise e

    except Exception as e:
        traceback.print_exc()
        print("❌ SYSTEM ERROR:", str(e))
        return JSONResponse(
            status_code=500,
            content={"detail": f"Backend crashed: {str(e)}"}
        )


    
@qc_router.get("/download-fixture-template")
def download_fixture_template():

    columns = [
        "event",
        "matchday",
        "matchday date",
        "competition",
        "match"
    ]

    df = pd.DataFrame(columns=columns)

    file_name = f"fixture_template_{int(time.time())}.xlsx"
    file_path = os.path.join(OUTPUT_FOLDER, file_name)

    df.to_excel(file_path, index=False)

    return FileResponse(
        path=file_path,
        filename=file_name,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@qc_router.get("/history")
def get_qc_history(db: Session = Depends(get_db)):
    """Fetches all QC audit history for the Manager Dashboard"""
    try:
        # Fetch all records, newest first
        records = db.query(RoscoSubmission).order_by(desc(RoscoSubmission.created_at)).all()
        return records
    except Exception as e:
        logger.error(f"❌ Error fetching history: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch QC history")


@qc_router.get("/history/weekly-export")
def export_qc_report(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """Generates a downloadable CSV report grouped by Rosco ID showing QC progress."""
    try:
        query = db.query(RoscoSubmission)

        # 1. Date Filtering Logic
        if start_date:
            dt_start = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.filter(RoscoSubmission.created_at >= dt_start)
        
        if end_date:
            # Add 1 day to the end date to make it inclusive (up to 23:59:59)
            dt_end = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
            query = query.filter(RoscoSubmission.created_at < dt_end)

        # If neither is provided, default to the last 7 days
        if not start_date and not end_date:
            query = query.filter(RoscoSubmission.created_at >= (func.now() - timedelta(days=7)))

        # Fetch records
        records = query.order_by(RoscoSubmission.created_at.asc()).all()

        # 2. Group by rosco_id
        grouped_data = {}
        for r in records:
            rid = r.rosco_id or r.manual_rosco_id or "UNKNOWN_ID"
            if rid not in grouped_data:
                grouped_data[rid] = []
            grouped_data[rid].append(r)

        # 3. Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        headers = [
            "Rosco ID", "Project Name", "Total Runs", 
            "First Run Date", "Latest Run Date",
            "Initial Processing Speed (rows/sec)", "Latest Processing Speed (rows/sec)", "Speed Progress",
            "Initial Errors", "Latest Errors", "Error Progress",
            "Initial Error Density (%)", "Latest Error Density (%)",
            "Latest Run Duration (s)", "Remaining Failed Rules (Latest)"
        ]
        writer.writerow(headers)

        # 4. Calculate metrics with safe null-checking (same as before)
        for rid, runs in grouped_data.items():
            first_run = runs[0]
            latest_run = runs[-1]
            total_runs = len(runs)

            def extract_stats(run):
                max_rows = 0
                total_evals = 0
                if run.qc_summary and isinstance(run.qc_summary, dict):
                    for rule, stats in run.qc_summary.items():
                        if isinstance(stats, dict):
                            evals = stats.get("Total_Evaluated", 0) or 0
                            total_evals += evals
                            if evals > max_rows: max_rows = evals
                                
                duration = run.run_duration or 0.0
                speed = (max_rows / duration) if duration > 0 else 0.0
                err_count = run.error_count or 0
                density = (err_count / total_evals * 100) if total_evals > 0 else 0.0
                return round(speed, 1), round(density, 1)

            first_speed, first_density = extract_stats(first_run)
            latest_speed, latest_density = extract_stats(latest_run)

            first_err_count = first_run.error_count or 0
            latest_err_count = latest_run.error_count or 0

            err_diff = latest_err_count - first_err_count
            err_progress = f"{abs(err_diff)} {'Fewer' if err_diff <= 0 else 'MORE'} Errors" if total_runs > 1 else "No prior runs"
            speed_diff = round(latest_speed - first_speed, 1)
            speed_progress = f"{'+' if speed_diff >= 0 else ''}{speed_diff} rows/s" if total_runs > 1 else "N/A"

            failed_rules = []
            if latest_run.qc_summary and isinstance(latest_run.qc_summary, dict):
                for rule, stats in latest_run.qc_summary.items():
                    if isinstance(stats, dict) and stats.get("Failed", 0) > 0:
                        failed_rules.append(f"{str(rule).replace('_', ' ').title()} ({stats['Failed']})")
            
            failed_str = " | ".join(failed_rules) if failed_rules else "Perfect Clean Run"
            first_date = first_run.created_at.strftime("%Y-%m-%d %H:%M") if first_run.created_at else "Unknown Date"
            latest_date = latest_run.created_at.strftime("%Y-%m-%d %H:%M") if latest_run.created_at else "Unknown Date"

            writer.writerow([
                rid, latest_run.project_name or "N/A", total_runs, first_date, latest_date,
                first_speed, latest_speed, speed_progress, first_err_count, latest_err_count,
                err_progress, f"{first_density}%", f"{latest_density}%",
                round(latest_run.run_duration or 0.0, 1), failed_str
            ])

        output.seek(0)
        
        # Name file dynamically based on dates provided
        date_label = f"{start_date}_to_{end_date}" if start_date and end_date else "Last_7_Days"
        filename = f"QC_Progress_Report_{date_label}.csv"
        
        return StreamingResponse(
            iter([output.getvalue()]), 
            media_type="text/csv", 
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except Exception as e:
        error_details = str(e)
        logger.error(f"❌ Error generating report: {error_details}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Detailed Error: {error_details}")


def clean_numeric_value(val):
    """Handles currency ($), commas, and Excel errors (#REF!, #N/A)."""
    if pd.isna(val) or val == "" or str(val).strip().upper() in ["#N/A", "NAN", "#REF!", "-", "0"]:
        return 0.0
    if isinstance(val, str):
        # Remove currency symbols and formatting
        val = val.replace('$', '').replace(',', '').strip()
    try:
        return float(val)
    except:
        return 0.0

# --- 2. Key Normalization (Fixes the 15:00 vs 15:15 issue) ---
def get_normalized_key(channel, dt_val, tm_val):
    """
    Normalizes keys by Date and Hour only. 
    This allows 15:15 in Export to match 15:00 in USA Data.
    """
    try:
        c = str(channel).strip().upper()
        # Ensure date is YYYY-MM-DD
        d = pd.to_datetime(dt_val).strftime('%Y-%m-%d')
        # Ensure time is just the Hour (24h format)
        h = pd.to_datetime(str(tm_val)).strftime('%H')
        return f"{c}_{d}_{h}"
    except:
        return "INVALID_KEY"

# --- 3. Main Logic Endpoint ---
# @qc_router.post("/calculate_usa_final_audit")
# def calculate_usa_final_audit(
#     usa_data: UploadFile = File(...),
#     export_file: UploadFile = File(...),
#     cpm_file: UploadFile = File(...)
# ):
#     timestamp = int(time.time())
#     UPLOAD_FOLDER = "uploads"
#     OUTPUT_FOLDER = "outputs"
#     os.makedirs(UPLOAD_FOLDER, exist_ok=True)
#     os.makedirs(OUTPUT_FOLDER, exist_ok=True)

#     usa_path = os.path.join(UPLOAD_FOLDER, f"usa_{timestamp}_{usa_data.filename}")
#     export_path = os.path.join(UPLOAD_FOLDER, f"exp_{timestamp}_{export_file.filename}")
#     cpm_path = os.path.join(UPLOAD_FOLDER, f"cpm_{timestamp}_{cpm_file.filename}")

#     try:
#         # Step 1: Save Uploaded Files
#         for f_obj, p in [(usa_data, usa_path), (export_file, export_path), (cpm_file, cpm_path)]:
#             with open(p, "wb") as f:
#                 shutil.copyfileobj(f_obj.file, f)

#         # Step 2: Load USA Data Workbook
#         # USA Main Headers start on Row 6 (skiprows=5)
#         xl_usa = pd.ExcelFile(usa_path)
#         sheet_map = {s.lower().replace(" ", ""): s for s in xl_usa.sheet_names}
        
#         usa_main_sheet = sheet_map.get('usadata', xl_usa.sheet_names[0])
#         df_usa_main = pd.read_excel(usa_path, sheet_name=usa_main_sheet, skiprows=5)
        
#         # Load Youtube and Table3 sheets if they exist
#         df_youtube = pd.read_excel(usa_path, sheet_name=sheet_map['youtube']) if 'youtube' in sheet_map else pd.DataFrame()
#         df_table3 = pd.read_excel(usa_path, sheet_name=sheet_map['table3']) if 'table3' in sheet_map else pd.DataFrame()

#         # Step 3: Load Export Template
#         # Export Headers start on Row 4 (skiprows=3)
#         df_export = pd.read_excel(export_path, skiprows=3)

#         # Step 4: Map USA Data Columns
#         usa_cols = df_usa_main.columns.tolist()
#         src_date = next((c for c in usa_cols if "Date" in str(c)), "Date")
#         src_start = next((c for c in usa_cols if "Start" in str(c)), "Start")
#         src_channel = next((c for c in usa_cols if "Channel" in str(c) or "Broadcaster" in str(c)), "TV-Channel")
#         src_aud = next((c for c in usa_cols if "Estimates" in str(c)), "Aud. Estimates ['000s]")

#         # Step 5: Create USA Lookup Map (Date + Hour logic)
#         df_usa_main['lookup_key'] = df_usa_main.apply(
#             lambda r: get_normalized_key(r[src_channel], r[src_date], r[src_start]), axis=1
#         )
#         # Convert to dictionary for high-speed lookup
#         usa_lookup_dict = df_usa_main.drop_duplicates(subset=['lookup_key']).set_index('lookup_key')[src_aud].to_dict()

#         # Step 6: Load CPM Data
#         # CPM Headers on Row 3 (skiprows=2)
#         df_cpm = pd.read_excel(cpm_path, skiprows=2)
#         df_cpm.rename(columns={df_cpm.columns[0]: 'DMA'}, inplace=True)
#         df_cpm['DMA'] = df_cpm['DMA'].astype(str).str.strip().str.upper()
        
#         # Match Excel's MONTH(TODAY())&"P2+"
#         target_demo = f"{datetime.now().month}P2+"

#         # Step 7: Apply Calculation Logic Row-by-Row
#         def run_calculations(row):
#             chan_raw = str(row.get('channel', ''))
#             chan_clean = chan_raw.lower().strip()
#             matchday = str(row.get('matchday', '')).strip().lower()
            
#             # --- A. Audience Calculation ---
#             audience = 0.0
#             if "youtube" in chan_clean and not df_youtube.empty:
#                 # Youtube uses Matchday VLOOKUP
#                 yt_match = df_youtube[df_youtube.iloc[:, 0].astype(str).str.strip().str.lower() == matchday]
#                 # Col Q (Index 16)
#                 audience = clean_numeric_value(yt_match.iloc[0, 16]) if not yt_match.empty else 0.0
#             else:
#                 # Standard Concat Key lookup
#                 exp_key = get_normalized_key(chan_raw, row['progr. start (date)'], row['progr. start (time)'])
#                 audience = usa_lookup_dict.get(exp_key, 0.0)

#             # --- B. Rate Calculation ---
#             rate = 0.0
#             if "youtube" in chan_clean and not df_youtube.empty:
#                 # Youtube VLOOKUP index 20 (Col T / Index 19)
#                 yt_match = df_youtube[df_youtube.iloc[:, 0].astype(str).str.strip().str.lower() == matchday]
#                 rate = clean_numeric_value(yt_match.iloc[0, 19]) if not yt_match.empty else 0.0
            
#             elif "peacock" in chan_clean and not df_table3.empty:
#                 # Peacock VLOOKUP Table3 index 3 (Col C / Index 2)
#                 pk_match = df_table3[df_table3.iloc[:, 0].astype(str).str.strip().str.lower() == matchday]
#                 rate = clean_numeric_value(pk_match.iloc[0, 2]) if not pk_match.empty else 0.0
            
#             else:
#                 # Standard CPM Calculation: (Aud * CPM) / 30 / 1.31
#                 chan_upper = chan_raw.strip().upper()
#                 if chan_upper in df_cpm['DMA'].values and target_demo in df_cpm.columns:
#                     cpm_val = clean_numeric_value(df_cpm.loc[df_cpm['DMA'] == chan_upper, target_demo].values[0])
#                     rate = (audience * cpm_val) / 30 / 1.31
            
#             return pd.Series([audience, rate])

#         # Execute and map back to Export columns
#         df_export[["aud_all_esti (000's)", "1sec Nielsen Rate in EUR"]] = df_export.apply(run_calculations, axis=1)

#         # Step 8: Save and Response
#         out_filename = f"USA_Audit_Calculated_{timestamp}.xlsx"
#         out_path = os.path.join(OUTPUT_FOLDER, out_filename)
#         df_export.to_excel(out_path, index=False)

#         return FileResponse(path=out_path, filename=out_filename)

#     except Exception as e:
#         # Log error detail for debugging
#         print(f"Error occurred: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))

@qc_router.post("/calculate_usa_final_audit")
async def calculate_usa_audit(
    usa_data: UploadFile = File(...),
    export_file: UploadFile = File(...),
    cpm_file: UploadFile = File(...)
):
    # This now returns a stream of logs followed by the file
    return StreamingResponse(
        process_usa_audit_logic_stream(
            usa_data, 
            export_file, 
            cpm_file, 
            UPLOAD_FOLDER  # Make sure your upload directory path is passed correctly
        ),
        media_type="text/event-stream"
    )

@qc_router.post("/calculate_mls_final_audit")
async def calculate_mls_audit(
    # MLS is mandatory, so it uses File(...)
    mls_data: UploadFile = File(...),
    # USA and Canada are optional individually, but one is required collectively
    usa_data: Optional[UploadFile] = File(None),
    canada_data: Optional[UploadFile] = File(None)
):
    # Safety check: Ensure at least one regional file is provided
    if not usa_data and not canada_data:
        raise HTTPException(
            status_code=400, 
            detail="At least one regional file (USA or Canada) must be provided along with MLS data."
        )

    # Returns a stream of logs followed by the base64 encoded file
    return StreamingResponse(
        process_mls_audit_logic_stream(
            mls_data=mls_data, 
            usa_data=usa_data, 
            canada_data=canada_data, 
            upload_folder=UPLOAD_FOLDER 
        ),
        media_type="text/event-stream"
    )

@qc_router.post("/calculate_japan_bsr_audit")
async def calculate_japan_audit(
    bsr_data: UploadFile = File(...),
    master_rates: UploadFile = File(...),
    rr_file: UploadFile = File(...),
    mm_file: UploadFile = File(...),
    event_id: int = Form(...),
    season: int = Form(...)
):
    # Convert uploaded files to BytesIO objects
    bsr_bytes = io.BytesIO(await bsr_data.read())
    rates_bytes = io.BytesIO(await master_rates.read())
    rr_bytes = io.BytesIO(await rr_file.read())
    mm_bytes = io.BytesIO(await mm_file.read())

    # Call the generator from the imported logic, passing the new params
    return StreamingResponse(
        process_japan_bsr(bsr_bytes, rates_bytes, rr_bytes, mm_bytes, event_id, season),
        media_type="text/event-stream"
    )

@qc_router.post("/calculate_intl_final_audit")
async def calculate_intl_audit(
    intl_data: UploadFile = File(...), 
    cpm_file: UploadFile = File(...),    
    euro_file: UploadFile = File(...),
    sport_genre: str = Form(...),      # Captures the Sport Genre from Frontend
    spot_fixture: str = Form(...)      # Captures the Spot Rate from Frontend
):
    """
    Endpoint to process the International Audit.
    Streams progress logs and returns a base64 encoded Excel file.
    """
    return StreamingResponse(
        process_intl_audit_logic_stream(
            intl_data,  
            cpm_file, 
            euro_file,
            sport_genre,               # Pass it into the logic stream
            spot_fixture,              # Pass it into the logic stream
            UPLOAD_FOLDER
        ),
        media_type="text/event-stream"
    )

# -------------------- 🌍 F1 MARKET CHECK ENDPOINT --------------------

EPL_CHECK_KEYS = {
    "impute_lt_live_status",
    "consolidate_gillete_soccer",
    "consolidate_soccer_sunday",
    "check_sky_showcase_live",
    "standardize_uk_ire_region",
    "check_fixture_vs_case",
    "check_pan_balkans_serbia_parity",
    "audit_multi_match_status",
    "check_date_time_format_integrity",
    "check_live_broadcast_uniqueness",
    "audit_channel_line_item_count",
    "check_combined_archive_status",
    "suppress_duplicated_audience",
    "harmonize_uk_ire_program_descriptions_strict",
    "check_game_of_the_day_match",
    "check_non_metered_primary_market_audience",
    "check_legacy_mapping",
    "check_premier_league_october_obligation",
    "filter_short_programs",
    "audit_ovn_whistle_to_whistle",
    "check_star_sports_3_consolidation",
    "check_bsa_nielsen_audience_presence",
    "audit_uk_ire_volume_consistency",
    
    # --- Newly Added (Missing from your snippet) ---
    "check_source_mediatype_validity",
    "sa_nielsen_inclusion_check",
    "epl_live_vs_delay_validation",
    "pl_magazine_highlights_classification",
    "audit_uk_ire_duplication_alignment",
    "audit_ott_broadcast_consolidation",
    "check_missing_live_games"
}

@qc_router.post("/market_check_and_process", response_model=None)
def market_check_and_process( 
    bsr_file: UploadFile = File(..., description="BSR file for market-specific checks"),
    obligation_file: Optional[UploadFile] = File(None, description="F1 Obligation file for broadcaster checks"), 
    overnight_file: Optional[UploadFile] = File(None, description="Overnight Audience file for upscale/integrity check"),
    macro_file: Optional[UploadFile] = File(None, description="Macro BSA Market Duplicator file"),
    checks: List[str] = Form(..., description="List of selected check keys"),
    check_configs: str = Form("{}", description="JSON string of runtime configurations"),
    
    # 🎯 NEW: Tracking Metadata from Frontend
    manual_rosco_id: Optional[str] = Form(None, description="Rosco ID"),
    destination_id: Optional[str] = Form(None, description="Delivery Target Date or ID"),
    project_name: Optional[str] = Form(None, description="Project Name"),
    user_name: Optional[str] = Form("System", description="User triggering the check"),
    
    # 🎯 NEW: Database Session
    db: Session = Depends(get_db)
):
    # Track execution time for analytics
    start_time = time.time()
    
    bsr_file_path = os.path.join(UPLOAD_FOLDER, bsr_file.filename)
    obligation_path, overnight_path, macro_path = None, None, None
    
    output_filename = f"Processed_BSR_{os.path.splitext(bsr_file.filename)[0]}_{int(time.time())}.xlsx"
    output_path = os.path.join(OUTPUT_FOLDER, output_filename)

    status_summaries = []
    df_processed = None 
    
    try:
        try:
            config_dict = json.loads(check_configs)
        except json.JSONDecodeError:
            config_dict = {}
            
        with open(bsr_file_path, "wb") as buffer:
            shutil.copyfileobj(bsr_file.file, buffer)
            
        if obligation_file and obligation_file.filename:
            obligation_path = os.path.join(UPLOAD_FOLDER, obligation_file.filename)
            with open(obligation_path, "wb") as buffer:
                shutil.copyfileobj(obligation_file.file, buffer)
                
        if overnight_file and overnight_file.filename: 
            overnight_path = os.path.join(UPLOAD_FOLDER, overnight_file.filename)
            with open(overnight_path, "wb") as buffer:
                shutil.copyfileobj(overnight_file.file, buffer)
                
        if macro_file and macro_file.filename: 
            macro_path = os.path.join(UPLOAD_FOLDER, macro_file.filename)
            with open(macro_path, "wb") as buffer:
                shutil.copyfileobj(macro_file.file, buffer)

        # Assuming EPL_CHECK_KEYS is defined somewhere above
        bsr_checks_to_run = [c for c in checks if c not in EPL_CHECK_KEYS]
        epl_checks_to_run = [c for c in checks if c in EPL_CHECK_KEYS]

        shared_kwargs = {
            'bsr_path': bsr_file_path, 
            'obligation_path': obligation_path, 
            'overnight_path': overnight_path, 
            'macro_path': macro_path
        }
        
        # Assuming BSRValidator and EPLValidator are imported/defined
        bsr_validator = BSRValidator(**shared_kwargs)
        epl_validator = EPLValidator(df=bsr_validator.df, **shared_kwargs)

        if bsr_checks_to_run:
            status_summaries.extend(bsr_validator.market_check_processor(bsr_checks_to_run))
            df_processed = bsr_validator.df 
        
        if epl_checks_to_run:
            if bsr_checks_to_run and df_processed is not None:
                epl_validator.df = df_processed
                
            epl_summaries = [epl_validator.market_check_map[c]() for c in epl_checks_to_run if c in epl_validator.market_check_map]
            status_summaries.extend(epl_summaries)
            df_processed = epl_validator.df 

        if df_processed is None:
            df_processed = bsr_validator.df 
        
        if df_processed.empty:
            raise Exception("Processed DataFrame is empty after applying checks.")

        clean_summaries = [s for s in status_summaries if isinstance(s, dict)]
        
        # -------------------------------------------------------------------
        # 🎯 SMART DB PARSER: Fixes missing 'rows_flagged' and builds DB Object
        # -------------------------------------------------------------------
        import re
        
        qc_summary_db = {}
        total_absolute_errors = 0
        base_total = len(df_processed) if df_processed is not None else 0

        for s in clean_summaries:
            check_name = s.get("action", s.get("check_key", "Unknown Check"))
            status = s.get("status", "Passed")
            desc = s.get("description", "")
            
            # 1. Ensure details dictionary exists
            if "details" not in s or not isinstance(s["details"], dict):
                s["details"] = {}
                
            fails = s["details"].get("rows_flagged", 0)
            
            # 2. MAGIC FIX: If the script forgot to set rows_flagged, extract it from the description string!
            if (fails == 0 or fails is None) and status in ['Flagged', 'Failed', 'Issue Found', 'Error']:
                match = re.search(r'[Ff]ound\s+(\d+)', desc)
                if match:
                    fails = int(match.group(1))
                else:
                    fails = 1 # Fallback so the DB knows it failed
                
                # INJECT IT BACK IN! This automatically fixes the UI "Anomalies" column!
                s["details"]["rows_flagged"] = fails
                
            # 3. Extract the Total Evaluated rows from the description
            match_eval = re.search(r'[Aa]udited\s+(\d+)\s+rows', desc)
            if match_eval:
                eval_total = int(match_eval.group(1))
            else:
                eval_total = base_total
                
            if fails > eval_total:
                eval_total = fails
                
            passes = eval_total - fails
            na = 0
            
            # 4. Handle Skipped checks safely
            if status == 'Skipped':
                passes = 0
                fails = 0
                na = eval_total
                s["details"]["rows_flagged"] = 0

            # 5. Assign to the Database Dictionary
            qc_summary_db[check_name] = {
                "Total_Evaluated": eval_total,
                "Passed": passes,
                "Failed": fails,
                "NA": na
            }
            total_absolute_errors += fails

        run_duration = time.time() - start_time
        
        # Save securely to PostgreSQL
        try:
            safe_rosco_id = manual_rosco_id or bsr_file.filename.split('.')[0]
            db_record = RoscoSubmission(
                rosco_id=safe_rosco_id,
                manual_rosco_id=manual_rosco_id,
                project_name=project_name,
                destination_id=destination_id,
                user_name=user_name,
                run_duration=round(run_duration, 2),
                error_count=total_absolute_errors,
                qc_summary=qc_summary_db,
                original_filename=bsr_file.filename
            )
            db.add(db_record)
            db.commit()
        except Exception as db_err:
            print(f"⚠️ Failed to save to database: {str(db_err)}")
        # -------------------------------------------------------------------

        # Save to Excel
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            df_processed.to_excel(writer, sheet_name='Processed BSR', index=False)
            
        download_url = f"/api/qc/download_file?filename={output_filename}" 

        return JSONResponse(content={
            "status": "Success",
            "message": f"Successfully applied {len(checks)} market checks.",
            "download_url": download_url,
            "summaries": clean_summaries # This now contains the fixed 'rows_flagged' data!
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred during market checks: {str(e)}")
        
    finally:
        for path in [bsr_file_path, obligation_path, overnight_path, macro_path]:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass

# -------------------- 📥 NEW DOWNLOAD ENDPOINT --------------------
@qc_router.get("/download_file")
async def download_file(filename: str = Query(...)):
    # 1. SANITIZE: Extract ONLY the file name, destroying any "../" or "/" characters
    safe_filename = os.path.basename(filename)
    
    # 2. RESOLVE: Create the absolute, real path on the server
    expected_dir = os.path.abspath(OUTPUT_FOLDER)
    file_path = os.path.abspath(os.path.join(expected_dir, safe_filename))

    # 3. VERIFY: Mathematically ensure the final path still starts with your expected directory
    if not file_path.startswith(expected_dir):
        raise HTTPException(status_code=403, detail="Forbidden: Invalid file path detected.")

    # --- DEBUG PRINTS ---
    print(f"DEBUG: Endpoint hit! Looking for file: {safe_filename}")
    print(f"DEBUG: Full path constructed: {file_path}")
    print(f"DEBUG: Does file exist? {os.path.exists(file_path)}")
    # --------------------

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found or link has expired.")
        
    return FileResponse(
        path=file_path,
        filename=safe_filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


# -------------------- 2. UPDATED LALIGA QC ENDPOINT --------------------
@qc_router.post("/api/run_laliga_qc")
def run_laliga_qc_checks(
    rosco_file: UploadFile = File(...),
    bsr_file: UploadFile = File(...),
    macro_file: UploadFile = File(...)
):
    config = load_config()
    col_map = config["column_mappings"]
    rules = config["qc_rules"]
    project = config["project_rules"]
    file_rules = config["file_rules"]

    rosco_path = os.path.join(UPLOAD_FOLDER, rosco_file.filename)
    bsr_path = os.path.join(UPLOAD_FOLDER, bsr_file.filename)
    macro_path = os.path.join(UPLOAD_FOLDER, macro_file.filename)
    
    try:
        with open(rosco_path, "wb") as buffer:
            shutil.copyfileobj(rosco_file.file, buffer)
        with open(bsr_path, "wb") as buffer:
            shutil.copyfileobj(bsr_file.file, buffer)
        with open(macro_path, "wb") as buffer:
            shutil.copyfileobj(macro_file.file, buffer)

        start_date, end_date = qc_general.detect_period_from_rosco(rosco_path)
        df = qc_general.load_bsr(bsr_path, col_map["bsr"])

        df.columns = df.columns.str.strip().str.replace("\xa0", " ", regex=True)
        df = df.applymap(lambda x: str(x).replace("\xa0", " ").strip() if isinstance(x, str) else x)
        df.rename(columns={"Start(UTC)": "Start (UTC)", "End(UTC)": "End (UTC)"}, inplace=True)

        df = qc_general.period_check(df, start_date, end_date, col_map["bsr"])
        df = qc_general.completeness_check(df, col_map["bsr"], rules)
        df = qc_general.overlap_duplicate_daybreak_check(df, col_map["bsr"], rules.get("overlap_check", {}))
        df = qc_general.program_category_check(bsr_path, df, col_map, rules.get("program_category", {}), file_rules)
        df = qc_general.check_event_matchday_competition(df, bsr_path, col_map, file_rules)
        df = qc_general.market_channel_consistency_check(df, rosco_path, col_map, file_rules)
        df = qc_general.rates_and_ratings_check(df, col_map["bsr"])
        df = qc_general.country_channel_id_check(df, col_map["bsr"])
        df = qc_general.client_lstv_ott_check(df, col_map["bsr"], rules.get("client_check", {}))
        
        df = qc_general.domestic_market_check(df, project, col_map["bsr"], debug=True)
        df = qc_general.duplicated_market_check(df, macro_path, project, col_map, file_rules, debug=True)

        df = qc_general.overlap_duplicate_daybreak_check(
            df, col_map["bsr"], rules.get("overlap_check", {})
        )

        output_prefix = file_rules.get("output_prefix", "Laliga_QC_Result_")
        output_sheet = file_rules.get("output_sheet_name", "Laliga QC Results")
        output_file = f"{output_prefix}{os.path.splitext(bsr_file.filename)[0]}.xlsx"
        output_path = os.path.join(OUTPUT_FOLDER, output_file)

        for col in df.select_dtypes(include=["datetimetz"]).columns:
            df[col] = df[col].dt.tz_convert(None).dt.tz_localize(None) if hasattr(df[col].dt, "tz") else df[col].dt.tz_localize(None)

        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name=output_sheet)

        qc_general.color_excel(output_path, df)
        qc_general.generate_summary_sheet(output_path, df, file_rules)

        return FileResponse(
            path=output_path,
            filename=output_file,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    except Exception as e:
        for path in [rosco_path, bsr_path, macro_path]:
            if path and os.path.exists(path): os.remove(path)
        raise HTTPException(status_code=500, detail=f"An error occurred during Laliga QC: {str(e)}")

# -------------------- EPL Endpoints --------------------

@qc_router.post("/api/run_epl_pre_checks")
def run_epl_pre_checks(
    notfinal_bsr: UploadFile = File(...),
    rosco_file: UploadFile = File(...),
    market_dup_file: UploadFile = File(...)
):
    bsr_path = os.path.join(UPLOAD_FOLDER, notfinal_bsr.filename)
    rosco_path = os.path.join(UPLOAD_FOLDER, rosco_file.filename)
    market_dup_path = os.path.join(UPLOAD_FOLDER, market_dup_file.filename)

    try:
        for obj, path in [
            (notfinal_bsr, bsr_path),
            (rosco_file, rosco_path),
            (market_dup_file, market_dup_path)
        ]:
            with open(path, "wb") as f:
                shutil.copyfileobj(obj.file, f)

        df = epl_checks.run_pre_checks(
            bsr_path=bsr_path,
            rosco_path=rosco_path,
            market_dup_path=market_dup_path
        )

        output_file = "EPL_Pre_Checks.xlsx"
        output_path = os.path.join(OUTPUT_FOLDER, output_file)

        df.to_excel(output_path, index=False)
        return FileResponse(output_path, filename=output_file)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@qc_router.post("/api/run_epl_post_checks")
def run_epl_post_checks(
    bsr_file: UploadFile = File(...),
    rosco_file: UploadFile = File(...),
    macro_file: UploadFile = File(...)
):
    bsr_path = os.path.join(UPLOAD_FOLDER, bsr_file.filename)
    rosco_path = os.path.join(UPLOAD_FOLDER, rosco_file.filename)
    macro_path = os.path.join(UPLOAD_FOLDER, macro_file.filename)

    try:
        for obj, path in [
            (bsr_file, bsr_path),
            (rosco_file, rosco_path),
            (macro_file, macro_path)
        ]:
            with open(path, "wb") as f:
                shutil.copyfileobj(obj.file, f)

        df = epl_checks.run_post_checks(
            bsr_path=bsr_path,
            rosco_path=rosco_path,
            macro_path=macro_path
        )

        output_file = "EPL_Post_Checks.xlsx"
        output_path = os.path.join(OUTPUT_FOLDER, output_file)

        df.to_excel(output_path, index=False)
        return FileResponse(output_path, filename=output_file)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ======================================================
# ================= SERIE A ============================
# ======================================================
@qc_router.post("/run_serie_a_qc")
def run_serie_a_qc(
    bsr_file: UploadFile = File(...),
    duplicator_file: Optional[UploadFile] = File(None),
    infront_file: Optional[UploadFile] = File(None),
    checks: List[str] = Form(...),
):
    bsr_path = os.path.join(UPLOAD_FOLDER, bsr_file.filename)
    dup_path = infront_path = None

    output_file = f"Serie_A_QC_Result_{int(time.time())}.xlsx"
    output_path = os.path.join(OUTPUT_FOLDER, output_file)

    try:
        with open(bsr_path, "wb") as f:
            shutil.copyfileobj(bsr_file.file, f)

        if duplicator_file:
            dup_path = os.path.join(UPLOAD_FOLDER, duplicator_file.filename)
            with open(dup_path, "wb") as f:
                shutil.copyfileobj(duplicator_file.file, f)

        if infront_file:
            infront_path = os.path.join(UPLOAD_FOLDER, infront_file.filename)
            with open(infront_path, "wb") as f:
                shutil.copyfileobj(infront_file.file, f)

        df = load_bsr(bsr_path)

        validator = SerieAValidator(
            df=df,
            duplicator_path=dup_path,
            infront_path=infront_path,
        )

        summaries = validator.market_check_processor(checks)
        df_processed = validator.df

        df_processed.to_excel(output_path, index=False)

        return JSONResponse(
            {
                "status": "Success",
                "download_url": f"/api/qc/download_file?filename={output_file}",
                "summaries": summaries,
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        for p in [bsr_path, dup_path, infront_path]:
            if p and os.path.exists(p):
                os.remove(p)


# -------------------- 📊 EARLY WARNING DASHBOARD ENDPOINT --------------------

# --- HARDCODED MASTER DATA ---
MANDATORY_CHANNELS = [
    "10 (AUS)", "10 Bold (AUS)", "7mate (AUS)", "ABC (USA)", "ABC 1 (AUS)", 
    "Abu Dhabi Sports 1 (MENA)", "Abu Dhabi Sports 2 (MENA)", "Arenasport 1 (Pan Balkans)", 
    "Arenasport 3P (Pan Balkans)", "Arenasport 5 (Pan Balkans)", "Arenasport 8 (Pan Balkans)", 
    "Ariana TV (AFG)", "Astro Grandstand (MYS)", "BandSports (BRA)", "BBC 1 (GBR)", 
    "beIN Sports (MENA)", "beIN Sports 1 (ASI)", "beIN Sports 1 (FRA)", "beIN Sports 1 (HKG)", 
    "beIN Sports 1 (MENA)", "beIN Sports 2 (MENA)", "beIN Sports 3 (ASI)", "beIN Sports 3 (AUS)", 
    "beIN Sports 3 (MENA)", "beIN Sports 3 (THA)", "beIN Sports 3 (TUR)", "beIN Sports 4 (MENA)", 
    "beIN Sports 4 (TUR)", "beIN Sports 5 (MENA)", "beIN Sports 6 (MENA)", "beIN Sports 8 (MENA)", 
    "beIN Sports AFC (MENA)", "beIN Sports AFC 1 (MENA)", "beIN Sports English 1 (MENA)", 
    "beIN Sports French 1 (MENA)", "beIN Sports French 2 (MENA)", "beIN Sports Xtra (USA)", 
    "Big Ten (USA)", "Canal 4 (SLV)", "Canal 5 (MEX)", "Canal+ Foot (FRA)", "Canal+ France (FRA)", 
    "Canal+ Live 1 (FRA)", "Canal+ Sport (CZE)", "Canal+ Sport (FRA)", "Canal+ Sport 2 (AFR)", 
    "Canal+ Sport 360 (FRA)", "Canale 5 (ITA)", "Caracol TV (COL)", "CBC (CAN)", "CBS (USA)", 
    "CCTV 16 Olympic (CHN)", "CCTV 5 (CHN)", "CCTV 5+ (CHN)", "CCTV Football (CHN)", 
    "Channel 4 (GBR)", "Channel 5 (GBR)", "Channel 7 (AUS)", "COSMOTE Sport 2 (GRC)", 
    "COSMOTE Sport 3 (GRC)", "COSMOTE Sport 5 (GRC)", "CT 1 (CZE)", "CT Sport (CZE)", 
    "Cytavision Sports 4 (CYP)", "DAZN 1 DE (DEU)", "DAZN 2 DE (DEU)", "DAZN DE (DEU)", 
    "DAZN ES (ESP)", "DAZN IT (ITA)", "DAZN JP (JPN)", "DAZN US (USA)", "discovery+ (GBR)", 
    "discovery+ (ITA)", "Disney+ (BRA)", "Disney+ LatAm South (LA)", "DSports (ARG)", 
    "DSports 2 (LA)", "DSports Motors (LA)", "ESPN (ARG)", "ESPN (AUS)", "ESPN (BRA)", 
    "ESPN (COL)", "ESPN (MEX)", "ESPN (NLD)", "ESPN (PCA)", "ESPN (USA)", "ESPN 2 (MEX)", 
    "ESPN 2 (NLD)", "ESPN 2 (PCA)", "ESPN 2 (USA)", "ESPN 3 (MEX)", "ESPN 3 (NLD)", 
    "ESPN 3 (PCA)", "ESPN 4 (ARG)", "ESPN 4 (BRA)", "ESPN Deportes (USA)", "ESPN+ (USA)", 
    "Eurosport (ASI)", "Eurosport (ESP)", "Eurosport (FRA)", "Eurosport (GBR)", 
    "Eurosport (ITA)", "Eurosport (NLD)", "Eurosport (PEU)", "Eurosport (POL)", 
    "Eurosport (PRT)", "Eurosport (ROU)", "Eurosport 2 (ESP)", "Eurosport 2 (FRA)", 
    "Eurosport 2 (ITA)", "Eurosport 2 (POL)", "Eurosport 2 (PRT)", "Eurosport 2 (ROU)", 
    "Flow Sports (CRB)", "Fox (USA)", "Fox 5 New York (USA)", "Fox Cricket (AUS)", 
    "Fox Footy (AUS)", "Fox League (AUS)", "Fox Soccer Plus (USA)", "Fox Sports (ARG)", 
    "Fox Sports (MEX)", "Fox Sports 1 (USA)", "Fox Sports 2 (MEX)", "Fox Sports 503 (AUS)", 
    "Fox Sports 505 (AUS)", "Fox Sports 506 (AUS)", "France 2 (FRA)", "France 3 (FRA)", 
    "Fuji TV 1 (JPN)", "Fuji TV 2 (JPN)", "Fuji TV Next (JPN)", "Gaora Sports (JPN)", 
    "GO! (AUS)", "Gol (ESP)", "Golf Channel (CZE)", "Golf Channel (LA)", "Golf Channel (THA)", 
    "Golf Channel HD Plus (THA)", "Golf Network (JPN)", "Golf por M+ (ESP)", 
    "Guangdong Sports Channel (CHN)", "Hub Premier 2 (SGP)", "Indosiar (IDN)", "iNews TV (IDN)", 
    "Infosport+ (FRA)", "iQiyi Sports (CHN)", "Italia 1 (ITA)", "ITV 1 (GBR)", "ITV 4 (GBR)", 
    "J Golf (KOR)", "J Sports 1 (JPN)", "J Sports 2 (JPN)", "J Sports 3 (JPN)", 
    "J Sports 4 (JPN)", "Jiangsu Sports (CHN)", "JOJ Sport (SVK)", "JOJ TV (SVK)", 
    "La 7 (ITA)", "LaLigaTV por M+ (ESP)", "Las Estrellas (MEX)", "L'Equipe (FRA)", 
    "L'Equipe (www) (FRA)", "M6 (FRA)", "MBC Action (MENA)", "Migu Video (CHN)", 
    "MLB Network (USA)", "Motor Trend (USA)", "Motorvision (DEU)", "MS Sport (DEU)", 
    "MSG (USA)", "MSG Sportsnet (USA)", "MTV Max (FIN)", "MTV Urheilu 1 (FIN)", "MTV3 (FIN)", 
    "NBA TV (USA)", "NBC (USA)", "NFL Network (USA)", "NHK 1 (JPN)", "NHL Network (USA)", 
    "Nippon TV (JPN)", "Nova Sport 2 (CZE)", "Nova Sport 3 (CZE)", "Nova Sport 4 (CZE)", 
    "Nova Sport 5 (CZE)", "Nova Sport 6 (CZE)", "Nova Sports 1 (GRC)", "Now Sports 2 (HKG)", 
    "Now Sports Golf 2 (HKG)", "Now Sports Premier League (HKG)", 
    "Now Sports Premier League 1 (HKG)", "NPO 1 (NLD)", "NTV G+ (JPN)", "One 2 (ISR)", 
    "ORF 1 (AUT)", "ORF Sport Plus (AUT)", "Play Sports 1 (BEL)", "Play Sports 2 (BEL)", 
    "Play Sports 3 (BEL)", "Play Sports 4 (BEL)", "RAI 1 (ITA)", "RAI 2 (ITA)", 
    "RAI Sport+ HD (ITA)", "Rally.TV (Global)", "RCN (COL)", "RCTI (IDN)", "RDS (CAN)", 
    "RSI 2 (CHE)", "RTL 7 (NLD)", "RTL Nitro (DEU)", "RTP 1 (PRT)", "RTP 2 (PRT)", 
    "RTS 2 (CHE)", "RTVS Sport (SVK)", "RUV television (ISL)", "SBS One (AUS)", 
    "SBS Viceland (AUS)", "SBT (BRA)", "SCTV (IDN)", "ServusTV (AUT)", 
    "Setanta Sports (Pan Baltic)", "Setanta Sports 2 Eurasia (CIS)", 
    "Setanta Sports Eurasia (CIS)", "SIC (PRT)", "SKY Sport 1 (NZL)", "Sky Sport Calcio (ITA)", 
    "Sky Sport F1 (ITA)", "Sky Sport Uno (ITA)", "Sky Sports 16 (MEX)", "Sky Sports 24 (MEX)", 
    "Sky Sports F1 (GBR)", "Sky Sports Golf (GBR)", "Sky Sports Main Event (GBR)", 
    "Sky Sports Mix (GBR)", "Sky Sports Premier League (GBR)", "SMG Great Sports (CHN)", 
    "SN East (CAN)", "SN One (CAN)", "SN Pacific (CAN)", "SN West (CAN)", "SNY (USA)", 
    "Sony Sports Ten 1 (IND)", "Sport 1 - myTeamTV (DEU)", "Sport 1 (CZE)", "Sport 1 (HUN)", 
    "Sport 1 (ISR)", "Sport 1 (UKR)", "Sport 18 - myTeamTV (DEU)", "Sport 2 - myTeamTV (DEU)", 
    "Sport 2 (CZE)", "Sport 2 (HUN)", "Sport 3 - myTeamTV (DEU)", "Sport 4 - myTeamTV (DEU)", 
    "Sport 5 - myTeamTV (DEU)", "Sport TV + (PRT)", "Sport TV 4 (PRT)", "Sportdeutschland.tv (DEU)", 
    "SportDigital (DEU)", "Sportitalia (ITA)", "Sportklub Golf (SVN)", "Sportslive + (JPN)", 
    "SportsMax 2 (CRB)", "Sportstars 3 (IDN)", "Sportstars 4 (IDN)", "SporTV (BRA)", 
    "SPOTV (IDN)", "SPOTV (MYS)", "SPOTV (SGP)", "SPOTV (THA)", "SPOTV 2 (IDN)", 
    "SPOTV 2 (MYS)", "SRF 1 (CHE)", "SRF 2 (CHE)", "SRF Info (CHE)", "Stan Sport (AUS)", 
    "Startimes World Football (AFR)", "SuperSport Action (AFR)", "SuperSport Football (AFR)", 
    "SuperSport Football Plus (AFR)", "SuperSport Golf (AFR)", "SuperSport GOtv Football (AFR)", 
    "SuperSport GOtv LaLiga (AFR)", "SuperSport LaLiga (AFR)", "SuperSport Maximo 1 (AFR)", 
    "SuperSport Maximo 1 (ZAF)", "SuperSport Maximo 3 (AFR)", "SuperSport Motorsport (AFR)", 
    "SuperSport Premier League (AFR)", "SuperSport Variety 1 (AFR)", "SuperSport Variety 1 (ZAF)", 
    "SuperSport Variety 2 (AFR)", "TBS (USA)", "TBS Channel (JPN)", "Telefe (ARG)", 
    "Telemundo (USA)", "Tencent QQ Live (CHN)", "Tencent QQ Sports (CHN)", "TF 1 (FRA)", 
    "TFX (FRA)", "The CW (USA)", "The Golf Channel (USA)", "Tivibu Spor (TUR)", "TLT (VEN)", 
    "TMC (FRA)", "TNT (BRA)", "TNT (USA)", "TNT Sports 1 (GBR)", "TNT Sports 2 (GBR)", 
    "TNT Sports 3 (GBR)", "Trans 7 (IDN)", "Tring Sport 1 (ALB)", "Tring Sport 2 (ALB)", 
    "TRT 1 (TUR)", "TRT Spor (TUR)", "TSN 1 (CAN)", "TSN 1 (MLT)", "TSN 2 (CAN)", 
    "TSN 3 (CAN)", "TSN 3 (MLT)", "TSN 4 (CAN)", "TSN 4 (MLT)", "TSN 5 (CAN)", "TSN+ (CAN)", 
    "TUDN (MEX)", "TUDN (USA)", "TV 2 Play (NOR)", "TV Asahi (JPN)", "TV Azteca 7 (MEX)", 
    "TV Bandeirantes (BRA)", "TV CG 2 (MNE)", "TV Globo (BRA)", "TV Osaka (JPN)", 
    "TV Tokyo (JPN)", "TV5 Monde Asie (ASI)", "TV5 Monde Europe (PEU)", 
    "TV5 Monde Maghreb (MENA)", "TV8 (ITA)", "TVA Sports (CAN)", "TVI (PRT)", "TVNZ 1 (NZL)", 
    "TVNZ Duke TV (NZL)", "UniMas (USA)", "Univision (USA)", "USA Network (USA)", 
    "V Sport Golf (DNK)", "V Sport Golf (FIN)", "V Sport Golf (SWE)", "V Sport Motor (SWE)", 
    "Viaplay (FIN)", "Viaplay (NLD)", "Viaplay (NOR)", "Viaplay (POL)", "Viaplay (SWE)", 
    "VTV 2 (VNM)", "WBZ Boston (USA)", "WOWOW Live (JPN)", "WOWOW Prime (JPN)", "YES (USA)", 
    "YLE TV2 (FIN)", "Ziggo Sport (NLD)", "Ziggo Sport 2 (NLD)", "Zona DAZN (ITA)"
]

# Simple Aura Master Data for mapping
AURA_MASTER_DATA = [
    # --- Argentina ---
    {"market": "argentina", "channel": "canal 9 ar", "id": "74"},
    {"market": "argentina", "channel": "canal 13 ar", "id": "74"},
    {"market": "argentina", "channel": "espn arg", "id": "74"},
    {"market": "argentina", "channel": "tyc sports", "id": "74"},
    {"market": "argentina", "channel": "canal 26 ar", "id": "74"},
    {"market": "argentina", "channel": "fox sports arg", "id": "74"},
    {"market": "argentina", "channel": "america 24", "id": "74"},
    {"market": "argentina", "channel": "cronica tv", "id": "74"},
    {"market": "argentina", "channel": "tn", "id": "74"},
    {"market": "argentina", "channel": "c5n", "id": "74"},
    {"market": "argentina", "channel": "espn 2 arg", "id": "74"},
    {"market": "argentina", "channel": "espn 3 arg", "id": "74"},
    {"market": "argentina", "channel": "ln+", "id": "74"},
    {"market": "argentina", "channel": "argentina 12", "id": "74"},
    {"market": "argentina", "channel": "espn premium arg", "id": "74"},
    {"market": "argentina", "channel": "america tv", "id": "74"},
    {"market": "argentina", "channel": "television publica argentina", "id": "74"},
    {"market": "argentina", "channel": "telefe", "id": "74"},
    {"market": "argentina", "channel": "net tv", "id": "74"},
    {"market": "argentina", "channel": "bravo tv", "id": "74"},
    {"market": "argentina", "channel": "tnt", "id": "74"},
    {"market": "argentina", "channel": "space", "id": "74"},
    # --- Australia ---
    {"market": "australia", "channel": "abc news", "id": "48"},
    {"market": "australia", "channel": "sbs world watch", "id": "48"},
    {"market": "australia", "channel": "10", "id": "48"},
    {"market": "australia", "channel": "10 bold", "id": "48"},
    {"market": "australia", "channel": "7 two", "id": "48"},
    {"market": "australia", "channel": "seven mate", "id": "48"},
    {"market": "australia", "channel": "9go", "id": "48"},
    {"market": "australia", "channel": "abc entertains", "id": "48"},
    {"market": "australia", "channel": "abc kids family", "id": "48"},
    {"market": "australia", "channel": "abc 1", "id": "48"},
    {"market": "australia", "channel": "nitv", "id": "48"},
    {"market": "australia", "channel": "nine", "id": "48"},
    {"market": "australia", "channel": "sbs one", "id": "48"},
    {"market": "australia", "channel": "sbs viceland", "id": "48"},
    {"market": "australia", "channel": "seven", "id": "48"},
    {"market": "australia", "channel": "gem", "id": "48"},
    {"market": "australia", "channel": "10 comedy", "id": "48"},
    # --- Austria ---
    {"market": "austria", "channel": "servustv at", "id": "1"},
    {"market": "austria", "channel": "rtl at", "id": "1"},
    {"market": "austria", "channel": "zdf (at)", "id": "1"},
    {"market": "austria", "channel": "ard (at)", "id": "1"},
    {"market": "austria", "channel": "dmax", "id": "1"},
    {"market": "austria", "channel": "eurosport at", "id": "1"},
    {"market": "austria", "channel": "orf sport+", "id": "1"},
    {"market": "austria", "channel": "kabel 1 doku", "id": "1"},
    {"market": "austria", "channel": "sat.1 gold", "id": "1"},
    {"market": "austria", "channel": "oe24 tv", "id": "1"},
    {"market": "austria", "channel": "puls 24", "id": "1"},
    {"market": "austria", "channel": "orf 1", "id": "1"},
    {"market": "austria", "channel": "orf 2", "id": "1"},
    {"market": "austria", "channel": "atv", "id": "1"},
    {"market": "austria", "channel": "puls 4", "id": "1"},
    {"market": "austria", "channel": "sat.1 at", "id": "1"},
    {"market": "austria", "channel": "pro7 at", "id": "1"},
    {"market": "austria", "channel": "vox at", "id": "1"},
    {"market": "austria", "channel": "kabel 1 at", "id": "1"},
    {"market": "austria", "channel": "rtl 2 at", "id": "1"},
    {"market": "austria", "channel": "3 sat at", "id": "1"},
    {"market": "austria", "channel": "arte", "id": "1"},
    {"market": "austria", "channel": "atv 2", "id": "1"},
    {"market": "austria", "channel": "kika", "id": "1"},
    {"market": "austria", "channel": "n-tv", "id": "1"},
    {"market": "austria", "channel": "rtl up", "id": "1"},
    {"market": "austria", "channel": "nitro", "id": "1"},
    {"market": "austria", "channel": "pro7 maxx", "id": "1"},
    {"market": "austria", "channel": "sport 1", "id": "1"},
    {"market": "austria", "channel": "tlc", "id": "1"},
    {"market": "austria", "channel": "sixx", "id": "1"},
    # --- Belgium ---
    {"market": "belgium", "channel": "vtm", "id": "83"},
    {"market": "belgium", "channel": "play", "id": "83"},
    {"market": "belgium", "channel": "play fiction", "id": "83"},
    {"market": "belgium", "channel": "vtm 3", "id": "83"},
    {"market": "belgium", "channel": "discovery channel vl", "id": "83"},
    {"market": "belgium", "channel": "comedy central", "id": "83"},
    {"market": "belgium", "channel": "nat geo fr", "id": "83"},
    {"market": "belgium", "channel": "vtm 4", "id": "83"},
    {"market": "belgium", "channel": "star channel", "id": "83"},
    {"market": "belgium", "channel": "mtv nl", "id": "83"},
    {"market": "belgium", "channel": "tlc", "id": "83"},
    {"market": "belgium", "channel": "play action", "id": "83"},
    {"market": "belgium", "channel": "investigation discovery", "id": "83"},
    {"market": "belgium", "channel": "ment 55", "id": "83"},
    {"market": "belgium", "channel": "hgtv", "id": "83"},
    {"market": "belgium", "channel": "ment pop", "id": "83"},
    {"market": "belgium", "channel": "eurosport nl", "id": "83"},
    {"market": "belgium", "channel": "vrt 1", "id": "83"},
    {"market": "belgium", "channel": "vrt canvas", "id": "83"},
    {"market": "belgium", "channel": "vtm 2", "id": "83"},
    {"market": "belgium", "channel": "nickelodeon", "id": "83"},
    {"market": "belgium", "channel": "disney channel vl", "id": "83"},
    {"market": "belgium", "channel": "dobbit tv", "id": "83"},
    {"market": "belgium", "channel": "njam", "id": "83"},
    {"market": "belgium", "channel": "studio 100", "id": "83"},
    {"market": "belgium", "channel": "kanaal z", "id": "83"},
    {"market": "belgium", "channel": "cartoon network", "id": "83"},
    {"market": "belgium", "channel": "nick jr nl", "id": "83"},
    {"market": "belgium", "channel": "plattelandstv", "id": "83"},
    {"market": "belgium", "channel": "eclips tv", "id": "83"},
    {"market": "belgium", "channel": "xite", "id": "83"},
    {"market": "belgium", "channel": "pickx+ nl", "id": "83"},
    {"market": "belgium", "channel": "tipik", "id": "83"},
    {"market": "belgium", "channel": "ab3", "id": "83"},
    {"market": "belgium", "channel": "tf1 bel", "id": "83"},
    {"market": "belgium", "channel": "mtv fr", "id": "83"},
    {"market": "belgium", "channel": "ln24", "id": "83"},
    {"market": "belgium", "channel": "tmc", "id": "83"},
    {"market": "belgium", "channel": "rtl tvi", "id": "83"},
    {"market": "belgium", "channel": "rtl club", "id": "83"},
    {"market": "belgium", "channel": "rtl plug", "id": "83"},
    {"market": "belgium", "channel": "la une", "id": "83"},
    {"market": "belgium", "channel": "abx", "id": "83"},
    {"market": "belgium", "channel": "nickelodeon fr", "id": "83"},
    {"market": "belgium", "channel": "disney channel fr", "id": "83"},
    {"market": "belgium", "channel": "canal z", "id": "83"},
    {"market": "belgium", "channel": "disney junior fr", "id": "83"},
    {"market": "belgium", "channel": "la trois", "id": "83"},
    {"market": "belgium", "channel": "pickx+ fr", "id": "83"},
    {"market": "belgium", "channel": "rtl district", "id": "83"},
    {"market": "belgium", "channel": "ketnet", "id": "83"},
    {"market": "belgium", "channel": "vtm non stop 90s", "id": "83"},
    {"market": "belgium", "channel": "atv", "id": "83"},
    {"market": "belgium", "channel": "france 2", "id": "83"},
    {"market": "belgium", "channel": "france 3", "id": "83"},
    # --- Brazil ---
    {"market": "brazil", "channel": "tv globo", "id": "78"},
    {"market": "brazil", "channel": "sbt", "id": "78"},
    {"market": "brazil", "channel": "globonews", "id": "78"},
    {"market": "brazil", "channel": "sportv 2 br", "id": "78"},
    {"market": "brazil", "channel": "sportv br", "id": "78"},
    {"market": "brazil", "channel": "band sports", "id": "78"},
    {"market": "brazil", "channel": "bandnews", "id": "78"},
    {"market": "brazil", "channel": "premiere clubes", "id": "78"},
    {"market": "brazil", "channel": "record news", "id": "78"},
    {"market": "brazil", "channel": "cnn", "id": "78"},
    {"market": "brazil", "channel": "espn bra", "id": "78"},
    {"market": "brazil", "channel": "espn 2 bra", "id": "78"},
    {"market": "brazil", "channel": "espn 4 bra", "id": "78"},
    {"market": "brazil", "channel": "telecine fun", "id": "78"},
    {"market": "brazil", "channel": "premiere 8 mosaico", "id": "78"},
    {"market": "brazil", "channel": "sportv 3 br", "id": "78"},
    {"market": "brazil", "channel": "canal uol", "id": "78"},
    {"market": "brazil", "channel": "jovem pan news", "id": "78"},
    {"market": "brazil", "channel": "xsports", "id": "78"},
    {"market": "brazil", "channel": "ge tv", "id": "78"},
    {"market": "brazil", "channel": "premiere 2", "id": "78"},
    {"market": "brazil", "channel": "premiere 3", "id": "78"},
    {"market": "brazil", "channel": "premiere 4", "id": "78"},
    {"market": "brazil", "channel": "premiere 5", "id": "78"},
    {"market": "brazil", "channel": "premiere 6", "id": "78"},
    {"market": "brazil", "channel": "premiere 7", "id": "78"},
    {"market": "brazil", "channel": "espn 3 bra", "id": "78"},
    {"market": "brazil", "channel": "espn 5 bra", "id": "78"},
    {"market": "brazil", "channel": "tv bandeirantes", "id": "78"},
    {"market": "brazil", "channel": "redetv", "id": "78"},
    {"market": "brazil", "channel": "rede record", "id": "78"},
    {"market": "brazil", "channel": "futura", "id": "78"},
    {"market": "brazil", "channel": "tv aparecida", "id": "78"},
    {"market": "brazil", "channel": "tv cultura", "id": "78"},
    {"market": "brazil", "channel": "telecine action", "id": "78"},
    {"market": "brazil", "channel": "telecine pipoca", "id": "78"},
    {"market": "brazil", "channel": "telecine premium", "id": "78"},
    {"market": "brazil", "channel": "tnt bra", "id": "78"},
    {"market": "brazil", "channel": "telecine touch", "id": "78"},
    {"market": "brazil", "channel": "telecine cult", "id": "78"},
    {"market": "brazil", "channel": "space bra", "id": "78"},
    # --- Bulgaria ---
    {"market": "bulgaria", "channel": "wness tv", "id": "5"},
    {"market": "bulgaria", "channel": "bnt 2", "id": "5"},
    {"market": "bulgaria", "channel": "bnt 3", "id": "5"},
    {"market": "bulgaria", "channel": "bulgaria on air", "id": "5"},
    {"market": "bulgaria", "channel": "diema sport", "id": "5"},
    {"market": "bulgaria", "channel": "diema sport 2", "id": "5"},
    {"market": "bulgaria", "channel": "diema sport 3", "id": "5"},
    {"market": "bulgaria", "channel": "tv evropa", "id": "5"},
    {"market": "bulgaria", "channel": "nova sport bg", "id": "5"},
    {"market": "bulgaria", "channel": "ring bg", "id": "5"},
    {"market": "bulgaria", "channel": "eurosport bg", "id": "5"},
    {"market": "bulgaria", "channel": "max sport 1", "id": "5"},
    {"market": "bulgaria", "channel": "max sport 2", "id": "5"},
    {"market": "bulgaria", "channel": "max sport 3", "id": "5"},
    {"market": "bulgaria", "channel": "max sport 4", "id": "5"},
    {"market": "bulgaria", "channel": "bnt 1", "id": "5"},
    {"market": "bulgaria", "channel": "bnt 4", "id": "5"},
    {"market": "bulgaria", "channel": "btv bg", "id": "5"},
    {"market": "bulgaria", "channel": "btv action", "id": "5"},
    {"market": "bulgaria", "channel": "eurocom", "id": "5"},
    {"market": "bulgaria", "channel": "nova news", "id": "5"},
    {"market": "bulgaria", "channel": "nova tv bg", "id": "5"},
    # --- Canada ---
    {"market": "canada", "channel": "cbc vancouver", "id": "49"},
    {"market": "canada", "channel": "chek", "id": "49"},
    {"market": "canada", "channel": "global bc", "id": "49"},
    {"market": "canada", "channel": "city vancouver", "id": "49"},
    {"market": "canada", "channel": "joytv 10", "id": "49"},
    {"market": "canada", "channel": "ctv two vancouver", "id": "49"},
    {"market": "canada", "channel": "omni 1", "id": "49"},
    {"market": "canada", "channel": "ctvvancouver", "id": "49"},
    {"market": "canada", "channel": "cbc calgary", "id": "49"},
    {"market": "canada", "channel": "cfcntv", "id": "49"},
    {"market": "canada", "channel": "city calgary", "id": "49"},
    {"market": "canada", "channel": "omni 2 ontario", "id": "49"},
    {"market": "canada", "channel": "cbc toronto", "id": "49"},
    {"market": "canada", "channel": "omni 1 ontorio", "id": "49"},
    {"market": "canada", "channel": "cftotv", "id": "49"},
    {"market": "canada", "channel": "chch", "id": "49"},
    {"market": "canada", "channel": "global ontario", "id": "49"},
    {"market": "canada", "channel": "city ontario", "id": "49"},
    {"market": "canada", "channel": "ctv two barrie", "id": "49"},
    {"market": "canada", "channel": "ctv news", "id": "49"},
    {"market": "canada", "channel": "vision", "id": "49"},
    {"market": "canada", "channel": "cbc news", "id": "49"},
    {"market": "canada", "channel": "much", "id": "49"},
    {"market": "canada", "channel": "cmt", "id": "49"},
    {"market": "canada", "channel": "ctv drama +", "id": "49"},
    {"market": "canada", "channel": "slice", "id": "49"},
    {"market": "canada", "channel": "usa network+", "id": "49"},
    {"market": "canada", "channel": "sn ontario", "id": "49"},
    {"market": "canada", "channel": "sn west", "id": "49"},
    {"market": "canada", "channel": "history", "id": "49"},
    {"market": "canada", "channel": "ctv scifi +", "id": "49"},
    {"market": "canada", "channel": "home network", "id": "49"},
    {"market": "canada", "channel": "sn 360", "id": "49"},
    {"market": "canada", "channel": "aptn", "id": "49"},
    {"market": "canada", "channel": "e", "id": "49"},
    {"market": "canada", "channel": "flavour network", "id": "49"},
    {"market": "canada", "channel": "ctv", "id": "49"},
    {"market": "canada", "channel": "ytv", "id": "49"},
    {"market": "canada", "channel": "ctv comedy +", "id": "49"},
    {"market": "canada", "channel": "dtour", "id": "49"},
    {"market": "canada", "channel": "cartoon+", "id": "49"},
    {"market": "canada", "channel": "showcase", "id": "49"},
    {"market": "canada", "channel": "sn", "id": "49"},
    {"market": "canada", "channel": "w network", "id": "49"},
    {"market": "canada", "channel": "global calgary", "id": "49"},
    {"market": "canada", "channel": "sn east", "id": "49"},
    {"market": "canada", "channel": "sn pacific", "id": "49"},
    {"market": "canada", "channel": "ctv two alberta", "id": "49"},
    {"market": "canada", "channel": "omni calgary", "id": "49"},
    {"market": "canada", "channel": "ctv 2", "id": "49"},
    {"market": "canada", "channel": "citytv", "id": "49"},
    {"market": "canada", "channel": "cp24", "id": "49"},
    {"market": "canada", "channel": "treehouse", "id": "49"},
    {"market": "canada", "channel": "tvo", "id": "49"},
    {"market": "canada", "channel": "cbxttv", "id": "49"},
    {"market": "canada", "channel": "city edmonton", "id": "49"},
    {"market": "canada", "channel": "yes tv edmonton", "id": "49"},
    {"market": "canada", "channel": "cfrntv", "id": "49"},
    {"market": "canada", "channel": "global edmonton", "id": "49"},
    {"market": "canada", "channel": "omni edmonton", "id": "49"},
    {"market": "canada", "channel": "fx canada", "id": "49"},
    {"market": "canada", "channel": "sn one", "id": "49"},
    {"market": "canada", "channel": "hbo canada", "id": "49"},
    {"market": "canada", "channel": "adult swim", "id": "49"},
    {"market": "canada", "channel": "ctv wild+", "id": "49"},
    {"market": "canada", "channel": "cbc montreal", "id": "49"},
    {"market": "canada", "channel": "city montreal", "id": "49"},
    {"market": "canada", "channel": "crime+ investigation", "id": "49"},
    {"market": "canada", "channel": "cfcftv", "id": "49"},
    {"market": "canada", "channel": "deja view", "id": "49"},
    {"market": "canada", "channel": "global quebec", "id": "49"},
    {"market": "canada", "channel": "h2", "id": "49"},
    {"market": "canada", "channel": "oxygen true crime+", "id": "49"},
    {"market": "canada", "channel": "knowledge bc", "id": "49"},
    {"market": "canada", "channel": "lifetime", "id": "49"},
    {"market": "canada", "channel": "movietime", "id": "49"},
    {"market": "canada", "channel": "national geographic", "id": "49"},
    {"market": "canada", "channel": "tln", "id": "49"},
    {"market": "canada", "channel": "ctv nature+", "id": "49"},
    {"market": "canada", "channel": "yes tv calgary", "id": "49"},
    {"market": "canada", "channel": "yes tv toronto", "id": "49"},
    {"market": "canada", "channel": "crave 1+4", "id": "49"},
    {"market": "canada", "channel": "cbc", "id": "49"},
    {"market": "canada", "channel": "natgeowild", "id": "49"},
    {"market": "canada", "channel": "ctv life+", "id": "49"},
    {"market": "canada", "channel": "ctv speed+", "id": "49"},
    {"market": "canada", "channel": "global tv", "id": "49"},
    {"market": "canada", "channel": "tsn 2", "id": "49"},
    {"market": "canada", "channel": "tsn 1", "id": "49"},
    {"market": "canada", "channel": "bravo", "id": "49"},
    {"market": "canada", "channel": "disney eng", "id": "49"},
    {"market": "canada", "channel": "cbftmontreal", "id": "49"},
    {"market": "canada", "channel": "noovo montreal", "id": "49"},
    {"market": "canada", "channel": "tva montreal", "id": "49"},
    {"market": "canada", "channel": "max", "id": "49"},
    {"market": "canada", "channel": "canal evasion", "id": "49"},
    {"market": "canada", "channel": "series", "id": "49"},
    {"market": "canada", "channel": "historia", "id": "49"},
    {"market": "canada", "channel": "tq total", "id": "49"},
    {"market": "canada", "channel": "z", "id": "49"},
    {"market": "canada", "channel": "canal d", "id": "49"},
    {"market": "canada", "channel": "tv5", "id": "49"},
    {"market": "canada", "channel": "canal vie", "id": "49"},
    {"market": "canada", "channel": "rdi", "id": "49"},
    {"market": "canada", "channel": "rds", "id": "49"},
    {"market": "canada", "channel": "artv", "id": "49"},
    {"market": "canada", "channel": "teletoon-f", "id": "49"},
    {"market": "canada", "channel": "tva", "id": "49"},
    {"market": "canada", "channel": "noovo total", "id": "49"},
    {"market": "canada", "channel": "src", "id": "49"},
    {"market": "canada", "channel": "rds 2", "id": "49"},
    {"market": "canada", "channel": "tva sports", "id": "49"},
    {"market": "canada", "channel": "investigation discovery", "id": "49"},
    {"market": "canada", "channel": "addiktv", "id": "49"},
    {"market": "canada", "channel": "casa", "id": "49"},
    {"market": "canada", "channel": "prise 2", "id": "49"},
    {"market": "canada", "channel": "tva sports 2", "id": "49"},
    {"market": "canada", "channel": "temoin", "id": "49"},
    {"market": "canada", "channel": "elle fictions", "id": "49"},
    {"market": "canada", "channel": "lcn", "id": "49"},
    {"market": "canada", "channel": "fight network", "id": "49"},
    {"market": "canada", "channel": "gametv", "id": "49"},
    # --- Chile ---
    {"market": "chile", "channel": "tnt sports", "id": "91"},
    {"market": "chile", "channel": "tnt sports premium", "id": "91"},
    {"market": "chile", "channel": "chilevision", "id": "91"},
    {"market": "chile", "channel": "mega", "id": "91"},
    {"market": "chile", "channel": "tvn cl", "id": "91"},
    {"market": "chile", "channel": "canal 13 cl", "id": "91"},
    {"market": "chile", "channel": "tv+", "id": "91"},
    {"market": "chile", "channel": "via x", "id": "91"},
    {"market": "chile", "channel": "24 horas", "id": "91"},
    {"market": "chile", "channel": "t13 en vivo", "id": "91"},
    {"market": "chile", "channel": "mega 2", "id": "91"},
    {"market": "chile", "channel": "espn chl", "id": "91"},
    {"market": "chile", "channel": "espn premium chl", "id": "91"},
    {"market": "chile", "channel": "espn 2 chl", "id": "91"},
    {"market": "chile", "channel": "espn 3 chl", "id": "91"},
    {"market": "chile", "channel": "espn 5 chl", "id": "91"},
    {"market": "chile", "channel": "espn 6 chl", "id": "91"},
    {"market": "chile", "channel": "espn 7 chl", "id": "91"},
    {"market": "chile", "channel": "canal 13c", "id": "91"},
    {"market": "chile", "channel": "ntv", "id": "91"},
    {"market": "chile", "channel": "rec tv", "id": "91"},
    # --- Colombia ---
    {"market": "colombia", "channel": "espn col", "id": "127"},
    {"market": "colombia", "channel": "espn 2 col", "id": "127"},
    {"market": "colombia", "channel": "espn 3 col", "id": "127"},
    {"market": "colombia", "channel": "espn 5 col", "id": "127"},
    {"market": "colombia", "channel": "espn 6 col", "id": "127"},
    {"market": "colombia", "channel": "espn 7 col", "id": "127"},
    {"market": "colombia", "channel": "rcn", "id": "127"},
    {"market": "colombia", "channel": "telemedellin", "id": "127"},
    {"market": "colombia", "channel": "city tv", "id": "127"},
    {"market": "colombia", "channel": "caracol tv", "id": "127"},
    {"market": "colombia", "channel": "las estrellas latinoamerica", "id": "127"},
    {"market": "colombia", "channel": "canal uno", "id": "127"},
    {"market": "colombia", "channel": "tnt", "id": "127"},
    {"market": "colombia", "channel": "cinecanal", "id": "127"},
    {"market": "colombia", "channel": "space", "id": "127"},
    {"market": "colombia", "channel": "tnt series", "id": "127"},
    # --- Croatia ---
    {"market": "croatia", "channel": "rtl hr", "id": "10"},
    {"market": "croatia", "channel": "doma tv", "id": "10"},
    {"market": "croatia", "channel": "rtl 2 hr", "id": "10"},
    {"market": "croatia", "channel": "croatian music channel", "id": "10"},
    {"market": "croatia", "channel": "sportska televizija", "id": "10"},
    {"market": "croatia", "channel": "star channel", "id": "10"},
    {"market": "croatia", "channel": "star life", "id": "10"},
    {"market": "croatia", "channel": "star crime", "id": "10"},
    {"market": "croatia", "channel": "star movies", "id": "10"},
    {"market": "croatia", "channel": "national geographic", "id": "10"},
    {"market": "croatia", "channel": "nat geo wild", "id": "10"},
    {"market": "croatia", "channel": "24 kitchen", "id": "10"},
    {"market": "croatia", "channel": "rtl crime", "id": "10"},
    {"market": "croatia", "channel": "rtl living", "id": "10"},
    {"market": "croatia", "channel": "cinestar tv", "id": "10"},
    {"market": "croatia", "channel": "cinestar action and thriller", "id": "10"},
    {"market": "croatia", "channel": "cinestar fantasy", "id": "10"},
    {"market": "croatia", "channel": "arena sport 1 hr", "id": "10"},
    {"market": "croatia", "channel": "arena sport 4 hr", "id": "10"},
    {"market": "croatia", "channel": "nova tv hr", "id": "10"},
    {"market": "croatia", "channel": "rtl kockica", "id": "10"},
    {"market": "croatia", "channel": "hrt 1", "id": "10"},
    {"market": "croatia", "channel": "hrt 2", "id": "10"},
    {"market": "croatia", "channel": "hrt 3", "id": "10"},
    {"market": "croatia", "channel": "hrt 4", "id": "10"},
    {"market": "croatia", "channel": "n1", "id": "10"},
    {"market": "croatia", "channel": "nickelodeon", "id": "10"},
    {"market": "croatia", "channel": "mini tv", "id": "10"},
    {"market": "croatia", "channel": "laudato tv", "id": "10"},
    {"market": "croatia", "channel": "arena sport 2 hr", "id": "10"},
    {"market": "croatia", "channel": "arena sport 3 hr", "id": "10"},
    {"market": "croatia", "channel": "klasik tv", "id": "10"},
    {"market": "croatia", "channel": "pickbox 1", "id": "10"},
    {"market": "croatia", "channel": "pickbox tv", "id": "10"},
    # --- Cyprus ---
    {"market": "cyprus", "channel": "rik 1", "id": "11"},
    {"market": "cyprus", "channel": "omega", "id": "11"},
    {"market": "cyprus", "channel": "ant 1", "id": "11"},
    {"market": "cyprus", "channel": "sigma tv", "id": "11"},
    {"market": "cyprus", "channel": "alpha kyproy", "id": "11"},
    {"market": "cyprus", "channel": "rik 2", "id": "11"},
    {"market": "cyprus", "channel": "cytavision sports 3", "id": "11"},
    {"market": "cyprus", "channel": "cytavision sports 3 public", "id": "11"},
    {"market": "cyprus", "channel": "cytavision sports 1", "id": "11"},
    {"market": "cyprus", "channel": "cytavision sports 1 cmaf (www)", "id": "11"},
    {"market": "cyprus", "channel": "cytavision sports 1 public", "id": "11"},
    {"market": "cyprus", "channel": "cytavision sports 4k", "id": "11"},
    {"market": "cyprus", "channel": "cytavision sports 3 hd cmaf", "id": "11"},
    {"market": "cyprus", "channel": "cytavision sports 4", "id": "11"},
    {"market": "cyprus", "channel": "cytavision sports 4 cmaf (www)", "id": "11"},
    {"market": "cyprus", "channel": "cytavision sports 4 public", "id": "11"},
    {"market": "cyprus", "channel": "cytavision sports 5", "id": "11"},
    {"market": "cyprus", "channel": "cytavision sports 5 cmaf (www)", "id": "11"},
    {"market": "cyprus", "channel": "cytavision sports 6 hd", "id": "11"},
    {"market": "cyprus", "channel": "cytavision sports 6 cmaf (www)", "id": "11"},
    {"market": "cyprus", "channel": "cytavision sports 8", "id": "11"},
    {"market": "cyprus", "channel": "cytavision sports 8 cmaf (www)", "id": "11"},
    {"market": "cyprus", "channel": "cytavision sports 7", "id": "11"},
    {"market": "cyprus", "channel": "cytavision sports 7 cmaf (www)", "id": "11"},
    {"market": "cyprus", "channel": "cytavision sports 7 public", "id": "11"},
    {"market": "cyprus", "channel": "cytavision sports 2", "id": "11"},
    {"market": "cyprus", "channel": "cytavision sports 2 cmaf (www)", "id": "11"},
    # --- Czech Republic ---
    {"market": "czech republic", "channel": "ct 2", "id": "12"},
    {"market": "czech republic", "channel": "ct 1", "id": "12"},
    {"market": "czech republic", "channel": "ct 24", "id": "12"},
    {"market": "czech republic", "channel": "ct sport", "id": "12"},
    {"market": "czech republic", "channel": "barrandov tv", "id": "12"},
    {"market": "czech republic", "channel": "cs film", "id": "12"},
    {"market": "czech republic", "channel": "ct art", "id": "12"},
    {"market": "czech republic", "channel": "kino barrandov", "id": "12"},
    {"market": "czech republic", "channel": "nova cz", "id": "12"},
    {"market": "czech republic", "channel": "prima cool", "id": "12"},
    {"market": "czech republic", "channel": "relax", "id": "12"},
    {"market": "czech republic", "channel": "nova fun", "id": "12"},
    {"market": "czech republic", "channel": "sport 1 cz", "id": "12"},
    {"market": "czech republic", "channel": "nova action", "id": "12"},
    {"market": "czech republic", "channel": "eurosport cz", "id": "12"},
    {"market": "czech republic", "channel": "cnn prima news", "id": "12"},
    {"market": "czech republic", "channel": "prima show", "id": "12"},
    {"market": "czech republic", "channel": "nova lady", "id": "12"},
    {"market": "czech republic", "channel": "canal+ sport cz", "id": "12"},
    {"market": "czech republic", "channel": "ct d", "id": "12"},
    {"market": "czech republic", "channel": "barrandov krimi", "id": "12"},
    {"market": "czech republic", "channel": "prima", "id": "12"},
    {"market": "czech republic", "channel": "cs mystery", "id": "12"},
    {"market": "czech republic", "channel": "joj cinema", "id": "12"},
    # --- Denmark ---
    {"market": "denmark", "channel": "dr 1", "id": "14"},
    {"market": "denmark", "channel": "dr 2", "id": "14"},
    {"market": "denmark", "channel": "dr ramasjang", "id": "14"},
    {"market": "denmark", "channel": "tv2 dk", "id": "14"},
    {"market": "denmark", "channel": "tv2 echo", "id": "14"},
    {"market": "denmark", "channel": "tv2 charlie", "id": "14"},
    {"market": "denmark", "channel": "tv2 sport dk", "id": "14"},
    {"market": "denmark", "channel": "tv2 news", "id": "14"},
    {"market": "denmark", "channel": "tv2 fri", "id": "14"},
    {"market": "denmark", "channel": "tv3 dk", "id": "14"},
    {"market": "denmark", "channel": "tv3 puls", "id": "14"},
    {"market": "denmark", "channel": "tv3 max dk", "id": "14"},
    {"market": "denmark", "channel": "kanal 5 dk", "id": "14"},
    {"market": "denmark", "channel": "kanal 4 dk", "id": "14"},
    {"market": "denmark", "channel": "investigation discovery", "id": "14"},
    {"market": "denmark", "channel": "discovery channel", "id": "14"},
    {"market": "denmark", "channel": "tlc", "id": "14"},
    {"market": "denmark", "channel": "canal 9 dk", "id": "14"},
    {"market": "denmark", "channel": "eurosport dk", "id": "14"},
    {"market": "denmark", "channel": "eurosport 2 dk", "id": "14"},
    {"market": "denmark", "channel": "ngc", "id": "14"},
    {"market": "denmark", "channel": "see", "id": "14"},
    {"market": "denmark", "channel": "tv2 sport x", "id": "14"},
    {"market": "denmark", "channel": "tv3+", "id": "14"},
    {"market": "denmark", "channel": "tv3 sport dk", "id": "14"},
    {"market": "denmark", "channel": "6 eren", "id": "14"},
    # --- Finland ---
    {"market": "finland", "channel": "yle tv1", "id": "30"},
    {"market": "finland", "channel": "yle tv2", "id": "30"},
    {"market": "finland", "channel": "mtv3", "id": "30"},
    {"market": "finland", "channel": "nelonen", "id": "30"},
    {"market": "finland", "channel": "sub", "id": "30"},
    {"market": "finland", "channel": "ava", "id": "30"},
    {"market": "finland", "channel": "star channel", "id": "30"},
    {"market": "finland", "channel": "jim", "id": "30"},
    {"market": "finland", "channel": "liv", "id": "30"},
    {"market": "finland", "channel": "tv5", "id": "30"},
    {"market": "finland", "channel": "mtv max", "id": "30"},
    {"market": "finland", "channel": "yle teema fem", "id": "30"},
    {"market": "finland", "channel": "yle teema", "id": "30"},
    {"market": "finland", "channel": "discovery channel", "id": "30"},
    {"market": "finland", "channel": "mtv urheilu 1", "id": "30"},
    {"market": "finland", "channel": "national geographic", "id": "30"},
    {"market": "finland", "channel": "mtv urheilu 2", "id": "30"},
    {"market": "finland", "channel": "eurosport fi", "id": "30"},
    {"market": "finland", "channel": "mtv urheilu 3", "id": "30"},
    {"market": "finland", "channel": "hero", "id": "30"},
    {"market": "finland", "channel": "kutonen", "id": "30"},
    # --- France ---
    {"market": "france", "channel": "france 2", "id": "16"},
    {"market": "france", "channel": "france 3", "id": "16"},
    {"market": "france", "channel": "m6", "id": "16"},
    {"market": "france", "channel": "cstar", "id": "16"},
    {"market": "france", "channel": "lequipe", "id": "16"},
    {"market": "france", "channel": "6ter", "id": "16"},
    {"market": "france", "channel": "canal+ foot", "id": "16"},
    {"market": "france", "channel": "canal+ sport fr", "id": "16"},
    {"market": "france", "channel": "canal+ sport 360", "id": "16"},
    {"market": "france", "channel": "tf1", "id": "16"},
    {"market": "france", "channel": "canal+ france", "id": "16"},
    {"market": "france", "channel": "france 5", "id": "16"},
    {"market": "france", "channel": "arte francais", "id": "16"},
    {"market": "france", "channel": "w9", "id": "16"},
    {"market": "france", "channel": "tmc", "id": "16"},
    {"market": "france", "channel": "tfx", "id": "16"},
    {"market": "france", "channel": "france 4", "id": "16"},
    {"market": "france", "channel": "gulli", "id": "16"},
    {"market": "france", "channel": "rmc story", "id": "16"},
    {"market": "france", "channel": "rmc decouverte", "id": "16"},
    {"market": "france", "channel": "bein sports 1 fr", "id": "16"},
    {"market": "france", "channel": "bein sports 2 fr", "id": "16"},
    {"market": "france", "channel": "bein sports 3 fr", "id": "16"},
    {"market": "france", "channel": "rmc sport 1", "id": "16"},
    {"market": "france", "channel": "rmc life", "id": "16"},
    # --- Germany ---
    {"market": "germany", "channel": "13th street", "id": "13"},
    {"market": "germany", "channel": "3 sat d", "id": "13"},
    {"market": "germany", "channel": "ard", "id": "13"},
    {"market": "germany", "channel": "ard-alpha", "id": "13"},
    {"market": "germany", "channel": "arte", "id": "13"},
    {"market": "germany", "channel": "bayerisches fernsehen", "id": "13"},
    {"market": "germany", "channel": "comedy central +1", "id": "13"},
    {"market": "germany", "channel": "c+i", "id": "13"},
    {"market": "germany", "channel": "comedy central", "id": "13"},
    {"market": "germany", "channel": "deluxe music", "id": "13"},
    {"market": "germany", "channel": "df1", "id": "13"},
    {"market": "germany", "channel": "discovery", "id": "13"},
    {"market": "germany", "channel": "disney channel", "id": "13"},
    {"market": "germany", "channel": "dmax", "id": "13"},
    {"market": "germany", "channel": "deutsches musik fernsehen", "id": "13"},
    {"market": "germany", "channel": "dokusat", "id": "13"},
    {"market": "germany", "channel": "geo", "id": "13"},
    {"market": "germany", "channel": "heimatkanal", "id": "13"},
    {"market": "germany", "channel": "hgtv", "id": "13"},
    {"market": "germany", "channel": "history", "id": "13"},
    {"market": "germany", "channel": "hr fernsehen", "id": "13"},
    {"market": "germany", "channel": "kabel 1 doku", "id": "13"},
    {"market": "germany", "channel": "kabel 1", "id": "13"},
    {"market": "germany", "channel": "mdr", "id": "13"},
    {"market": "germany", "channel": "mtv germany", "id": "13"},
    {"market": "germany", "channel": "n-tv", "id": "13"},
    {"market": "germany", "channel": "n24 doku", "id": "13"},
    {"market": "germany", "channel": "national geographic", "id": "13"},
    {"market": "germany", "channel": "nat. geowi", "id": "13"},
    {"market": "germany", "channel": "ndr", "id": "13"},
    {"market": "germany", "channel": "nick deutschland", "id": "13"},
    {"market": "germany", "channel": "nitro", "id": "13"},
    {"market": "germany", "channel": "ard one", "id": "13"},
    {"market": "germany", "channel": "pro7 maxx", "id": "13"},
    {"market": "germany", "channel": "passion", "id": "13"},
    {"market": "germany", "channel": "phoenix", "id": "13"},
    {"market": "germany", "channel": "pro7", "id": "13"},
    {"market": "germany", "channel": "rbb", "id": "13"},
    {"market": "germany", "channel": "romance tv", "id": "13"},
    {"market": "germany", "channel": "rtl", "id": "13"},
    {"market": "germany", "channel": "rtl crime", "id": "13"},
    {"market": "germany", "channel": "rtl 2", "id": "13"},
    {"market": "germany", "channel": "rtl living", "id": "13"},
    {"market": "germany", "channel": "rtlup", "id": "13"},
    {"market": "germany", "channel": "sat.1 gold", "id": "13"},
    {"market": "germany", "channel": "sat.1", "id": "13"},
    {"market": "germany", "channel": "schlager deluxe", "id": "13"},
    {"market": "germany", "channel": "sixx", "id": "13"},
    {"market": "germany", "channel": "sky krimi", "id": "13"},
    {"market": "germany", "channel": "sky documentaries", "id": "13"},
    {"market": "germany", "channel": "sky nature", "id": "13"},
    {"market": "germany", "channel": "sky atlantic", "id": "13"},
    {"market": "germany", "channel": "sky sport bundesliga de", "id": "13"},
    {"market": "germany", "channel": "sky cinema action", "id": "13"},
    {"market": "germany", "channel": "sky cinema classics", "id": "13"},
    {"market": "germany", "channel": "sky cinema family", "id": "13"},
    {"market": "germany", "channel": "sky cinema highlights", "id": "13"},
    {"market": "germany", "channel": "sky cinema premiere", "id": "13"},
    {"market": "germany", "channel": "sky sport golf de", "id": "13"},
    {"market": "germany", "channel": "skyone hd", "id": "13"},
    {"market": "germany", "channel": "sky sport premier league de", "id": "13"},
    {"market": "germany", "channel": "sky showcase de", "id": "13"},
    {"market": "germany", "channel": "sky sport f1 de", "id": "13"},
    {"market": "germany", "channel": "sky sport tennis de", "id": "13"},
    {"market": "germany", "channel": "sky sport top event de", "id": "13"},
    {"market": "germany", "channel": "sport1 d", "id": "13"},
    {"market": "germany", "channel": "sr fernsehen", "id": "13"},
    {"market": "germany", "channel": "super rtl", "id": "13"},
    {"market": "germany", "channel": "sw fernsehen", "id": "13"},
    {"market": "germany", "channel": "swr fernsehen bw", "id": "13"},
    {"market": "germany", "channel": "swr fernsehen rp", "id": "13"},
    {"market": "germany", "channel": "syfy", "id": "13"},
    {"market": "germany", "channel": "tagesschau 24", "id": "13"},
    {"market": "germany", "channel": "tele 5", "id": "13"},
    {"market": "germany", "channel": "tlc", "id": "13"},
    {"market": "germany", "channel": "toggo plus", "id": "13"},
    {"market": "germany", "channel": "universal channel", "id": "13"},
    {"market": "germany", "channel": "vox", "id": "13"},
    {"market": "germany", "channel": "vox up", "id": "13"},
    {"market": "germany", "channel": "warner tv comedy", "id": "13"},
    {"market": "germany", "channel": "warner tv film", "id": "13"},
    {"market": "germany", "channel": "warner tv serie", "id": "13"},
    {"market": "germany", "channel": "wdr", "id": "13"},
    {"market": "germany", "channel": "welt", "id": "13"},
    {"market": "germany", "channel": "zdf", "id": "13"},
    {"market": "germany", "channel": "zdf info", "id": "13"},
    {"market": "germany", "channel": "zdf neo", "id": "13"},
    {"market": "germany", "channel": "kika", "id": "13"},
    {"market": "germany", "channel": "mdr sn", "id": "13"},
    {"market": "germany", "channel": "mdr st", "id": "13"},
    {"market": "germany", "channel": "mdr th", "id": "13"},
    {"market": "germany", "channel": "ndr hh", "id": "13"},
    {"market": "germany", "channel": "ndr mv", "id": "13"},
    {"market": "germany", "channel": "ndr ni", "id": "13"},
    {"market": "germany", "channel": "ndr sh", "id": "13"},
    {"market": "germany", "channel": "radio bremen tv", "id": "13"},
    {"market": "germany", "channel": "rbb berlin", "id": "13"},
    {"market": "germany", "channel": "rbb brandenburg", "id": "13"},
    {"market": "germany", "channel": "rtl hessen", "id": "13"},
    {"market": "germany", "channel": "rtl hh sh", "id": "13"},
    {"market": "germany", "channel": "rtl ni-hb", "id": "13"},
    {"market": "germany", "channel": "rtl west", "id": "13"},
    {"market": "germany", "channel": "sat.1 bayern", "id": "13"},
    {"market": "germany", "channel": "sat.1 hh-sh", "id": "13"},
    {"market": "germany", "channel": "sat.1 ni-hb", "id": "13"},
    {"market": "germany", "channel": "sat.1 nrw", "id": "13"},
    {"market": "germany", "channel": "sat.1 rp-he", "id": "13"},
    {"market": "germany", "channel": "sky sport mix de", "id": "13"},
    {"market": "germany", "channel": "sky sport news de", "id": "13"},
    {"market": "germany", "channel": "sky sport 1 de", "id": "13"},
    {"market": "germany", "channel": "sky sport 2 de", "id": "13"},
    {"market": "germany", "channel": "sky sport 3 de", "id": "13"},
    {"market": "germany", "channel": "sky sport 4 de", "id": "13"},
    {"market": "germany", "channel": "sky sport 5 de", "id": "13"},
    {"market": "germany", "channel": "eurosport de", "id": "13"},
    {"market": "germany", "channel": "dazn 1 de", "id": "13"},
    {"market": "germany", "channel": "dazn 2 de", "id": "13"},
    {"market": "germany", "channel": "sky sport 6 de", "id": "13"},
    {"market": "germany", "channel": "sky sport 7 de", "id": "13"},
    {"market": "germany", "channel": "sky sport bundesliga 1", "id": "13"},
    {"market": "germany", "channel": "sky sport bundesliga 2", "id": "13"},
    {"market": "germany", "channel": "sky sport bundesliga 3", "id": "13"},
    {"market": "germany", "channel": "sky sport bundesliga 4", "id": "13"},
    {"market": "germany", "channel": "sky sport bundesliga 5", "id": "13"},
    {"market": "germany", "channel": "sky sport bundesliga 6", "id": "13"},
    {"market": "germany", "channel": "sky sport bundesliga 7", "id": "13"},
    {"market": "germany", "channel": "sky sport 8 de", "id": "13"},
    {"market": "germany", "channel": "sky sport 10 de", "id": "13"},
    {"market": "germany", "channel": "sky sport 9 de", "id": "13"},
    # --- Greece ---
    {"market": "greece", "channel": "ert 1", "id": "17"},
    {"market": "greece", "channel": "ert 2", "id": "17"},
    {"market": "greece", "channel": "alpha", "id": "17"},
    {"market": "greece", "channel": "makedonia tv", "id": "17"},
    {"market": "greece", "channel": "ert 3", "id": "17"},
    {"market": "greece", "channel": "skai", "id": "17"},
    {"market": "greece", "channel": "mega", "id": "17"},
    {"market": "greece", "channel": "nickelodeon", "id": "17"},
    {"market": "greece", "channel": "nickelodeon +", "id": "17"},
    {"market": "greece", "channel": "ant 1", "id": "17"},
    {"market": "greece", "channel": "star", "id": "17"},
    {"market": "greece", "channel": "open beyond", "id": "17"},
    {"market": "greece", "channel": "novasports premier league gr", "id": "17"},
    {"market": "greece", "channel": "novasports 5 gr", "id": "17"},
    {"market": "greece", "channel": "novasports start gr", "id": "17"},
    {"market": "greece", "channel": "novasports news gr", "id": "17"},
    {"market": "greece", "channel": "novasports extra 2", "id": "17"},
    {"market": "greece", "channel": "novasports 2 gr", "id": "17"},
    {"market": "greece", "channel": "novasports prime gr", "id": "17"},
    {"market": "greece", "channel": "novasports 4 gr", "id": "17"},
    # --- Hungary ---
    {"market": "hungary", "channel": "izaura", "id": "18"},
    {"market": "hungary", "channel": "spiler 1", "id": "18"},
    {"market": "hungary", "channel": "sorozat+", "id": "18"},
    {"market": "hungary", "channel": "spiler 2", "id": "18"},
    {"market": "hungary", "channel": "hir tv", "id": "18"},
    {"market": "hungary", "channel": "ozone tv", "id": "18"},
    {"market": "hungary", "channel": "m1", "id": "18"},
    {"market": "hungary", "channel": "teennick", "id": "18"},
    {"market": "hungary", "channel": "muzsika tv", "id": "18"},
    {"market": "hungary", "channel": "national geographic", "id": "18"},
    {"market": "hungary", "channel": "tlc", "id": "18"},
    {"market": "hungary", "channel": "id", "id": "18"},
    {"market": "hungary", "channel": "atv spirit", "id": "18"},
    {"market": "hungary", "channel": "viasat 2", "id": "18"},
    {"market": "hungary", "channel": "travel channel", "id": "18"},
    {"market": "hungary", "channel": "nick jr.", "id": "18"},
    {"market": "hungary", "channel": "nat geo wild", "id": "18"},
    {"market": "hungary", "channel": "cool", "id": "18"},
    {"market": "hungary", "channel": "discovery channel", "id": "18"},
    {"market": "hungary", "channel": "history", "id": "18"},
    {"market": "hungary", "channel": "tv2 kids", "id": "18"},
    {"market": "hungary", "channel": "rtl hu", "id": "18"},
    {"market": "hungary", "channel": "rtl ketto", "id": "18"},
    {"market": "hungary", "channel": "film+", "id": "18"},
    {"market": "hungary", "channel": "cartoon network", "id": "18"},
    {"market": "hungary", "channel": "cartoonito", "id": "18"},
    {"market": "hungary", "channel": "tv2 comedy", "id": "18"},
    {"market": "hungary", "channel": "slager tv", "id": "18"},
    {"market": "hungary", "channel": "eurosport hu", "id": "18"},
    {"market": "hungary", "channel": "tv2 sef", "id": "18"},
    {"market": "hungary", "channel": "prime hu", "id": "18"},
    {"market": "hungary", "channel": "jocky tv", "id": "18"},
    {"market": "hungary", "channel": "nicktoons", "id": "18"},
    {"market": "hungary", "channel": "tv2 klub", "id": "18"},
    {"market": "hungary", "channel": "viasat 3", "id": "18"},
    {"market": "hungary", "channel": "paramount network", "id": "18"},
    {"market": "hungary", "channel": "zenebutik", "id": "18"},
    {"market": "hungary", "channel": "nickelodeon", "id": "18"},
    {"market": "hungary", "channel": "viasat 6", "id": "18"},
    {"market": "hungary", "channel": "moziverzum", "id": "18"},
    {"market": "hungary", "channel": "tv4", "id": "18"},
    {"market": "hungary", "channel": "viasat film", "id": "18"},
    {"market": "hungary", "channel": "comedy central", "id": "18"},
    {"market": "hungary", "channel": "duna tv", "id": "18"},
    {"market": "hungary", "channel": "axn", "id": "18"},
    {"market": "hungary", "channel": "rtl harom (duplicate)", "id": "18"},
    {"market": "hungary", "channel": "disney channel", "id": "18"},
    {"market": "hungary", "channel": "life tv", "id": "18"},
    {"market": "hungary", "channel": "atv", "id": "18"},
    {"market": "hungary", "channel": "super tv2 hu", "id": "18"},
    {"market": "hungary", "channel": "galaxy4", "id": "18"},
    {"market": "hungary", "channel": "rtl gold", "id": "18"},
    {"market": "hungary", "channel": "m2", "id": "18"},
    {"market": "hungary", "channel": "film4", "id": "18"},
    {"market": "hungary", "channel": "tv2 hu", "id": "18"},
    {"market": "hungary", "channel": "match4", "id": "18"},
    {"market": "hungary", "channel": "duna world", "id": "18"},
    {"market": "hungary", "channel": "m4 sport", "id": "18"},
    {"market": "hungary", "channel": "m5", "id": "18"},
    {"market": "hungary", "channel": "arena4", "id": "18"},
    {"market": "hungary", "channel": "mozi+", "id": "18"},
    {"market": "hungary", "channel": "m4 sport+", "id": "18"},
    # --- India ---
    {"market": "india", "channel": "colors cineplex", "id": "59"},
    {"market": "india", "channel": "asianet", "id": "59"},
    {"market": "india", "channel": "asianet movies", "id": "59"},
    {"market": "india", "channel": "asianet news", "id": "59"},
    {"market": "india", "channel": "asianet plus", "id": "59"},
    {"market": "india", "channel": "star suvarna", "id": "59"},
    {"market": "india", "channel": "star suvarnaa plus", "id": "59"},
    {"market": "india", "channel": "colors", "id": "59"},
    {"market": "india", "channel": "colors hd", "id": "59"},
    {"market": "india", "channel": "dd national", "id": "59"},
    {"market": "india", "channel": "dd news", "id": "59"},
    {"market": "india", "channel": "dd sports", "id": "59"},
    {"market": "india", "channel": "discovery turbo in", "id": "59"},
    {"market": "india", "channel": "india news", "id": "59"},
    {"market": "india", "channel": "news 18", "id": "59"},
    {"market": "india", "channel": "kolkata tv", "id": "59"},
    {"market": "india", "channel": "star sports 1 kannada", "id": "59"},
    {"market": "india", "channel": "star maa gold", "id": "59"},
    {"market": "india", "channel": "star maa", "id": "59"},
    {"market": "india", "channel": "star gold 2", "id": "59"},
    {"market": "india", "channel": "mtv", "id": "59"},
    {"market": "india", "channel": "news 24", "id": "59"},
    {"market": "india", "channel": "news 9", "id": "59"},
    {"market": "india", "channel": "news live", "id": "59"},
    {"market": "india", "channel": "news nation", "id": "59"},
    {"market": "india", "channel": "news x", "id": "59"},
    {"market": "india", "channel": "polimer tv", "id": "59"},
    {"market": "india", "channel": "eurosport in", "id": "59"},
    {"market": "india", "channel": "sony sab", "id": "59"},
    {"market": "india", "channel": "sony max 2", "id": "59"},
    {"market": "india", "channel": "sony pal", "id": "59"},
    {"market": "india", "channel": "sony pix", "id": "59"},
    {"market": "india", "channel": "sony pix hd", "id": "59"},
    {"market": "india", "channel": "star gold hd", "id": "59"},
    {"market": "india", "channel": "star gold", "id": "59"},
    {"market": "india", "channel": "star jalsha", "id": "59"},
    {"market": "india", "channel": "star plus hd", "id": "59"},
    {"market": "india", "channel": "star plus", "id": "59"},
    {"market": "india", "channel": "star pravah", "id": "59"},
    {"market": "india", "channel": "star sports 1 india", "id": "59"},
    {"market": "india", "channel": "star sports 1 hindi", "id": "59"},
    {"market": "india", "channel": "star sports 1 hd india", "id": "59"},
    {"market": "india", "channel": "star utsav", "id": "59"},
    {"market": "india", "channel": "star vijay", "id": "59"},
    {"market": "india", "channel": "sony sports ten 2", "id": "59"},
    {"market": "india", "channel": "sony sports ten 3 hindi", "id": "59"},
    {"market": "india", "channel": "sony sports ten 1 hd", "id": "59"},
    {"market": "india", "channel": "sony sports ten 1", "id": "59"},
    {"market": "india", "channel": "star vijay hd", "id": "59"},
    {"market": "india", "channel": "zee action", "id": "59"},
    {"market": "india", "channel": "star gold 2 hd", "id": "59"},
    {"market": "india", "channel": "zee news", "id": "59"},
    {"market": "india", "channel": "zee tv", "id": "59"},
    {"market": "india", "channel": "zee tv hd", "id": "59"},
    {"market": "india", "channel": "mtv hd", "id": "59"},
    {"market": "india", "channel": "star sports 1 hd hindi", "id": "59"},
    {"market": "india", "channel": "eurosport in hd", "id": "59"},
    {"market": "india", "channel": "asianet hd", "id": "59"},
    {"market": "india", "channel": "flowers tv", "id": "59"},
    {"market": "india", "channel": "news 7 tamil", "id": "59"},
    {"market": "india", "channel": "tv5 monde asie", "id": "59"},
    {"market": "india", "channel": "star jalsha hd", "id": "59"},
    {"market": "india", "channel": "star sports select 1 hd", "id": "59"},
    {"market": "india", "channel": "cineplex hd", "id": "59"},
    {"market": "india", "channel": "star sports select 2 hd", "id": "59"},
    {"market": "india", "channel": "sony sab hd", "id": "59"},
    {"market": "india", "channel": "star gold select hd", "id": "59"},
    {"market": "india", "channel": "star maa hd", "id": "59"},
    {"market": "india", "channel": "star sports 1 tamil", "id": "59"},
    {"market": "india", "channel": "star sports select 1", "id": "59"},
    {"market": "india", "channel": "star sports select 2", "id": "59"},
    {"market": "india", "channel": "star gold select", "id": "59"},
    {"market": "india", "channel": "star sports 2 kannada", "id": "59"},
    {"market": "india", "channel": "star suvarna hd", "id": "59"},
    {"market": "india", "channel": "sony sports ten 2 hd", "id": "59"},
    {"market": "india", "channel": "sony sports ten 3 hindi hd", "id": "59"},
    {"market": "india", "channel": "star bharat", "id": "59"},
    {"market": "india", "channel": "star bharat hd", "id": "59"},
    {"market": "india", "channel": "star sports 1 telugu", "id": "59"},
    {"market": "india", "channel": "star sports khel", "id": "59"},
    {"market": "india", "channel": "star sports 1 hd tamil", "id": "59"},
    {"market": "india", "channel": "star sports 1 hd telugu", "id": "59"},
    {"market": "india", "channel": "star sports 2 telugu", "id": "59"},
    {"market": "india", "channel": "sony yay", "id": "59"},
    {"market": "india", "channel": "sony max", "id": "59"},
    {"market": "india", "channel": "sony sports ten 5 hd", "id": "59"},
    {"market": "india", "channel": "sony sports ten 5", "id": "59"},
    {"market": "india", "channel": "star sports 2 india", "id": "59"},
    {"market": "india", "channel": "star sports 2 hd india", "id": "59"},
    {"market": "india", "channel": "sony max hd", "id": "59"},
    {"market": "india", "channel": "star sports 3 india", "id": "59"},
    {"market": "india", "channel": "star sports 2 hindi", "id": "59"},
    {"market": "india", "channel": "star sports 2 hd hindi", "id": "59"},
    {"market": "india", "channel": "star sports 2 tamil", "id": "59"},
    {"market": "india", "channel": "news j", "id": "59"},
    # --- Indonesia ---
    {"market": "indonesia", "channel": "cnn ind", "id": "52"},
    {"market": "indonesia", "channel": "metro tv", "id": "52"},
    {"market": "indonesia", "channel": "tv one id", "id": "52"},
    {"market": "indonesia", "channel": "kompas tv", "id": "52"},
    {"market": "indonesia", "channel": "btv", "id": "52"},
    {"market": "indonesia", "channel": "transtv", "id": "52"},
    {"market": "indonesia", "channel": "inews tv", "id": "52"},
    {"market": "indonesia", "channel": "tvri 1", "id": "52"},
    {"market": "indonesia", "channel": "tvri sport", "id": "52"},
    {"market": "indonesia", "channel": "sportstars 2", "id": "52"},
    {"market": "indonesia", "channel": "btv pay", "id": "52"},
    {"market": "indonesia", "channel": "mnc soccer channel", "id": "52"},
    {"market": "indonesia", "channel": "idx channel", "id": "52"},
    {"market": "indonesia", "channel": "mnc news", "id": "52"},
    {"market": "indonesia", "channel": "sportstars", "id": "52"},
    {"market": "indonesia", "channel": "sportstars 4", "id": "52"},
    {"market": "indonesia", "channel": "sportstars 3", "id": "52"},
    {"market": "indonesia", "channel": "moji", "id": "52"},
    {"market": "indonesia", "channel": "sctv", "id": "52"},
    {"market": "indonesia", "channel": "rcti", "id": "52"},
    {"market": "indonesia", "channel": "global tv", "id": "52"},
    {"market": "indonesia", "channel": "garuda tv", "id": "52"},
    {"market": "indonesia", "channel": "rtv", "id": "52"},
    {"market": "indonesia", "channel": "indosiar", "id": "52"},
    {"market": "indonesia", "channel": "antv indonesia", "id": "52"},
    {"market": "indonesia", "channel": "mnc tv", "id": "52"},
    {"market": "indonesia", "channel": "trans 7", "id": "52"},
    {"market": "indonesia", "channel": "mdtv", "id": "52"},
    {"market": "indonesia", "channel": "hanacaraka tv", "id": "52"},
    {"market": "indonesia", "channel": "lifestyle and fashion", "id": "52"},
    {"market": "indonesia", "channel": "music channel", "id": "52"},
    {"market": "indonesia", "channel": "mnc entertainment", "id": "52"},
    {"market": "indonesia", "channel": "drama channel", "id": "52"},
    # --- Ireland ---
    {"market": "ireland", "channel": "rte 1", "id": "20"},
    {"market": "ireland", "channel": "rte 1 +1", "id": "20"},
    {"market": "ireland", "channel": "rte 2", "id": "20"},
    {"market": "ireland", "channel": "rte 2 +1", "id": "20"},
    {"market": "ireland", "channel": "virgin media one", "id": "20"},
    {"market": "ireland", "channel": "virgin media one +1", "id": "20"},
    {"market": "ireland", "channel": "virgin media two", "id": "20"},
    {"market": "ireland", "channel": "virgin media three", "id": "20"},
    {"market": "ireland", "channel": "virgin media four", "id": "20"},
    {"market": "ireland", "channel": "tg4", "id": "20"},
    {"market": "ireland", "channel": "channel 4", "id": "20"},
    {"market": "ireland", "channel": "channel 4 +1", "id": "20"},
    {"market": "ireland", "channel": "more4", "id": "20"},
    {"market": "ireland", "channel": "e4", "id": "20"},
    {"market": "ireland", "channel": "film4", "id": "20"},
    {"market": "ireland", "channel": "comedy central", "id": "20"},
    {"market": "ireland", "channel": "comedy central extra", "id": "20"},
    {"market": "ireland", "channel": "discovery", "id": "20"},
    {"market": "ireland", "channel": "discovery id", "id": "20"},
    {"market": "ireland", "channel": "mtv", "id": "20"},
    {"market": "ireland", "channel": "nickelodeon", "id": "20"},
    {"market": "ireland", "channel": "nick jr", "id": "20"},
    {"market": "ireland", "channel": "nicktoons", "id": "20"},
    {"market": "ireland", "channel": "nick jr too", "id": "20"},
    {"market": "ireland", "channel": "sky showcase ire", "id": "20"},
    {"market": "ireland", "channel": "sky news", "id": "20"},
    {"market": "ireland", "channel": "sky sports main event", "id": "20"},
    {"market": "ireland", "channel": "sky sports golf", "id": "20"},
    {"market": "ireland", "channel": "sky sports premier league", "id": "20"},
    {"market": "ireland", "channel": "sky sports tennis ire", "id": "20"},
    {"market": "ireland", "channel": "sky sports football", "id": "20"},
    {"market": "ireland", "channel": "sky sports racing", "id": "20"},
    {"market": "ireland", "channel": "sky sports news", "id": "20"},
    {"market": "ireland", "channel": "sky witness", "id": "20"},
    {"market": "ireland", "channel": "sky atlantic", "id": "20"},
    {"market": "ireland", "channel": "sky comedy", "id": "20"},
    {"market": "ireland", "channel": "sky documentaries", "id": "20"},
    {"market": "ireland", "channel": "sky arts", "id": "20"},
    {"market": "ireland", "channel": "sky nature", "id": "20"},
    {"market": "ireland", "channel": "sky max", "id": "20"},
    {"market": "ireland", "channel": "sky crime", "id": "20"},
    {"market": "ireland", "channel": "sky mix", "id": "20"},
    {"market": "ireland", "channel": "tlc", "id": "20"},
    {"market": "ireland", "channel": "challenge", "id": "20"},
    {"market": "ireland", "channel": "u+dave", "id": "20"},
    {"market": "ireland", "channel": "gold", "id": "20"},
    {"market": "ireland", "channel": "alibi", "id": "20"},
    {"market": "ireland", "channel": "u+w", "id": "20"},
    {"market": "ireland", "channel": "really", "id": "20"},
    {"market": "ireland", "channel": "u+drama", "id": "20"},
    {"market": "ireland", "channel": "true crime", "id": "20"},
    {"market": "ireland", "channel": "true crime xtra", "id": "20"},
    {"market": "ireland", "channel": "food network", "id": "20"},
    {"market": "ireland", "channel": "dmax ir", "id": "20"},
    {"market": "ireland", "channel": "hgtv", "id": "20"},
    {"market": "ireland", "channel": "quest red", "id": "20"},
    {"market": "ireland", "channel": "quest", "id": "20"},
    {"market": "ireland", "channel": "great tv", "id": "20"},
    {"market": "ireland", "channel": "great mystery", "id": "20"},
    {"market": "ireland", "channel": "great romance", "id": "20"},
    {"market": "ireland", "channel": "premier sports 1 ire", "id": "20"},
    {"market": "ireland", "channel": "rtejr", "id": "20"},
    {"market": "ireland", "channel": "bbc1", "id": "20"},
    {"market": "ireland", "channel": "bbc2", "id": "20"},
    {"market": "ireland", "channel": "tnt sports 1", "id": "20"},
    # --- Italy ---
    {"market": "italy", "channel": "rai 3", "id": "19"},
    {"market": "italy", "channel": "rai movie", "id": "19"},
    {"market": "italy", "channel": "rete 4", "id": "19"},
    {"market": "italy", "channel": "rai 1", "id": "19"},
    {"market": "italy", "channel": "rai 2", "id": "19"},
    {"market": "italy", "channel": "rai 5", "id": "19"},
    {"market": "italy", "channel": "rai scuola", "id": "19"},
    {"market": "italy", "channel": "rai storia", "id": "19"},
    {"market": "italy", "channel": "rai sport+ hd", "id": "19"},
    {"market": "italy", "channel": "rai premium", "id": "19"},
    {"market": "italy", "channel": "rai yoyo", "id": "19"},
    {"market": "italy", "channel": "canale 5", "id": "19"},
    {"market": "italy", "channel": "italia 1", "id": "19"},
    {"market": "italy", "channel": "la 5", "id": "19"},
    {"market": "italy", "channel": "top crime", "id": "19"},
    {"market": "italy", "channel": "la 7", "id": "19"},
    {"market": "italy", "channel": "la 7 cinema", "id": "19"},
    {"market": "italy", "channel": "rai news 24", "id": "19"},
    {"market": "italy", "channel": "20 mediaset", "id": "19"},
    {"market": "italy", "channel": "cielo", "id": "19"},
    {"market": "italy", "channel": "sky atlantic", "id": "19"},
    {"market": "italy", "channel": "sky cinema action", "id": "19"},
    {"market": "italy", "channel": "sky cinema collection", "id": "19"},
    {"market": "italy", "channel": "sky cinema comedy", "id": "19"},
    {"market": "italy", "channel": "sky cinema drama", "id": "19"},
    {"market": "italy", "channel": "sky cinema romance", "id": "19"},
    {"market": "italy", "channel": "sky cinema suspense", "id": "19"},
    {"market": "italy", "channel": "sky cinema uno", "id": "19"},
    {"market": "italy", "channel": "sky cinema uno +24", "id": "19"},
    {"market": "italy", "channel": "sky on demand 1 hd", "id": "19"},
    {"market": "italy", "channel": "sky sport 24 it", "id": "19"},
    {"market": "italy", "channel": "sky sport arena it", "id": "19"},
    {"market": "italy", "channel": "sky sport f1 it", "id": "19"},
    {"market": "italy", "channel": "sky sport moto gp it", "id": "19"},
    {"market": "italy", "channel": "sky sport nba it", "id": "19"},
    {"market": "italy", "channel": "sky sport uno it", "id": "19"},
    {"market": "italy", "channel": "sky tg 24", "id": "19"},
    {"market": "italy", "channel": "sky tg24 (50)", "id": "19"},
    {"market": "italy", "channel": "sky uno", "id": "19"},
    {"market": "italy", "channel": "tv 8 it", "id": "19"},
    {"market": "italy", "channel": "sky documentaries", "id": "19"},
    {"market": "italy", "channel": "sky investigation", "id": "19"},
    {"market": "italy", "channel": "sky nature", "id": "19"},
    {"market": "italy", "channel": "sky serie", "id": "19"},
    {"market": "italy", "channel": "sky serie +1", "id": "19"},
    {"market": "italy", "channel": "sky sport 4k", "id": "19"},
    {"market": "italy", "channel": "sky sport calcio it", "id": "19"},
    {"market": "italy", "channel": "sky sport tennis it", "id": "19"},
    {"market": "italy", "channel": "sky sport golf it", "id": "19"},
    {"market": "italy", "channel": "sky sport max it", "id": "19"},
    {"market": "italy", "channel": "iris", "id": "19"},
    {"market": "italy", "channel": "sky cinema family", "id": "19"},
    {"market": "italy", "channel": "sky sport 251 it", "id": "19"},
    {"market": "italy", "channel": "sky sport 252 it", "id": "19"},
    {"market": "italy", "channel": "sky sport 253 it", "id": "19"},
    {"market": "italy", "channel": "sky sport 255 it", "id": "19"},
    {"market": "italy", "channel": "sky sport 256 it", "id": "19"},
    {"market": "italy", "channel": "sky sport 257 it", "id": "19"},
    {"market": "italy", "channel": "sky sport 258 it", "id": "19"},
    {"market": "italy", "channel": "sky sport 254 it", "id": "19"},
    {"market": "italy", "channel": "sky sport 259 it", "id": "19"},
    {"market": "italy", "channel": "sky cinema 2", "id": "19"},
    {"market": "italy", "channel": "sky cinema 2+24", "id": "19"},
    {"market": "italy", "channel": "sky uno+1", "id": "19"},
    # --- Japan ---
    {"market": "japan", "channel": "fuji tv", "id": "44"},
    {"market": "japan", "channel": "nippon tv", "id": "44"},
    {"market": "japan", "channel": "tbs jpn", "id": "44"},
    {"market": "japan", "channel": "tv asahi", "id": "44"},
    {"market": "japan", "channel": "tv tokyo", "id": "44"},
    {"market": "japan", "channel": "ytv", "id": "44"},
    {"market": "japan", "channel": "ctv", "id": "44"},
    {"market": "japan", "channel": "nbn", "id": "44"},
    {"market": "japan", "channel": "abc", "id": "44"},
    {"market": "japan", "channel": "ktv", "id": "44"},
    {"market": "japan", "channel": "mbs tv", "id": "44"},
    {"market": "japan", "channel": "tv osaka", "id": "44"},
    {"market": "japan", "channel": "cbc", "id": "44"},
    {"market": "japan", "channel": "thk", "id": "44"},
    {"market": "japan", "channel": "tv aichi", "id": "44"},
    {"market": "japan", "channel": "nhk educational", "id": "44"},
    {"market": "japan", "channel": "nhk", "id": "44"},
    {"market": "japan", "channel": "nhk bs", "id": "44"},
    # --- Malaysia ---
    {"market": "malaysia", "channel": "cgtn", "id": "85"},
    {"market": "malaysia", "channel": "cnn hd", "id": "85"},
    {"market": "malaysia", "channel": "bernama dtt", "id": "85"},
    {"market": "malaysia", "channel": "astro awani", "id": "85"},
    {"market": "malaysia", "channel": "bernama tv", "id": "85"},
    {"market": "malaysia", "channel": "bein sports my", "id": "85"},
    {"market": "malaysia", "channel": "btv", "id": "85"},
    {"market": "malaysia", "channel": "abc australia", "id": "85"},
    {"market": "malaysia", "channel": "al-jazeera english", "id": "85"},
    {"market": "malaysia", "channel": "al-jazeera english hd", "id": "85"},
    {"market": "malaysia", "channel": "bbc", "id": "85"},
    {"market": "malaysia", "channel": "bbc hd", "id": "85"},
    {"market": "malaysia", "channel": "cnbc", "id": "85"},
    {"market": "malaysia", "channel": "golf channel hd", "id": "85"},
    {"market": "malaysia", "channel": "nhk", "id": "85"},
    {"market": "malaysia", "channel": "astro arena hd", "id": "85"},
    {"market": "malaysia", "channel": "astro arena 2 hd", "id": "85"},
    {"market": "malaysia", "channel": "tvs", "id": "85"},
    {"market": "malaysia", "channel": "sukan rtm dtt", "id": "85"},
    {"market": "malaysia", "channel": "tvb jade", "id": "85"},
    {"market": "malaysia", "channel": "berita rtm", "id": "85"},
    {"market": "malaysia", "channel": "tv 1 (mys)", "id": "85"},
    {"market": "malaysia", "channel": "tv 3 (mys)", "id": "85"},
    {"market": "malaysia", "channel": "astro aec", "id": "85"},
    {"market": "malaysia", "channel": "astro aec hd", "id": "85"},
    {"market": "malaysia", "channel": "sun tv", "id": "85"},
    {"market": "malaysia", "channel": "tv okey", "id": "85"},
    {"market": "malaysia", "channel": "tv okey dtt", "id": "85"},
    {"market": "malaysia", "channel": "tv alhijrah", "id": "85"},
    {"market": "malaysia", "channel": "awesome tv", "id": "85"},
    {"market": "malaysia", "channel": "astro ria hd", "id": "85"},
    {"market": "malaysia", "channel": "8tv", "id": "85"},
    {"market": "malaysia", "channel": "tv 2 (mys)", "id": "85"},
    {"market": "malaysia", "channel": "ntv 7", "id": "85"},
    {"market": "malaysia", "channel": "tv 9 (mys)", "id": "85"},
    {"market": "malaysia", "channel": "kbs", "id": "85"},
    {"market": "malaysia", "channel": "kbsw hd", "id": "85"},
    {"market": "malaysia", "channel": "tv6", "id": "85"},
    # --- Mexico ---
    {"market": "mexico", "channel": "espn 2 mex", "id": "64"},
    {"market": "mexico", "channel": "espn 3 mex", "id": "64"},
    {"market": "mexico", "channel": "fox sports mex", "id": "64"},
    {"market": "mexico", "channel": "fox sports 2 mex", "id": "64"},
    {"market": "mexico", "channel": "fox sports 3 mex", "id": "64"},
    {"market": "mexico", "channel": "las estrellas", "id": "64"},
    {"market": "mexico", "channel": "tv azteca uno", "id": "64"},
    {"market": "mexico", "channel": "adn noticias", "id": "64"},
    {"market": "mexico", "channel": "telehit", "id": "64"},
    {"market": "mexico", "channel": "espn mex", "id": "64"},
    {"market": "mexico", "channel": "tv mexiquense", "id": "64"},
    {"market": "mexico", "channel": "las estrellas -2hrs", "id": "64"},
    {"market": "mexico", "channel": "teleformula", "id": "64"},
    {"market": "mexico", "channel": "tudn mex", "id": "64"},
    {"market": "mexico", "channel": "n+ foro", "id": "64"},
    {"market": "mexico", "channel": "imagen tv", "id": "64"},
    {"market": "mexico", "channel": "canal 4 guadalajara", "id": "64"},
    {"market": "mexico", "channel": "multimedios", "id": "64"},
    {"market": "mexico", "channel": "canal 4 monterrey", "id": "64"},
    {"market": "mexico", "channel": "canal 8 monterrey", "id": "64"},
    {"market": "mexico", "channel": "mas vision", "id": "64"},
    {"market": "mexico", "channel": "tv unam", "id": "64"},
    {"market": "mexico", "channel": "multimedios cdmx", "id": "64"},
    {"market": "mexico", "channel": "6.1 multimedios guadalajara", "id": "64"},
    {"market": "mexico", "channel": "milenio tv", "id": "64"},
    {"market": "mexico", "channel": "adrenalina sports network", "id": "64"},
    {"market": "mexico", "channel": "aym sports", "id": "64"},
    {"market": "mexico", "channel": "mvs tv paga", "id": "64"},
    {"market": "mexico", "channel": "canal 5", "id": "64"},
    {"market": "mexico", "channel": "las estrellas -1hr", "id": "64"},
    {"market": "mexico", "channel": "a+", "id": "64"},
    {"market": "mexico", "channel": "canal catorce", "id": "64"},
    {"market": "mexico", "channel": "aprende+", "id": "64"},
    {"market": "mexico", "channel": "tv azteca 7", "id": "64"},
    {"market": "mexico", "channel": "once", "id": "64"},
    {"market": "mexico", "channel": "canal 22", "id": "64"},
    {"market": "mexico", "channel": "animal planet", "id": "64"},
    {"market": "mexico", "channel": "canal 22.2", "id": "64"},
    {"market": "mexico", "channel": "nu9ve", "id": "64"},
    {"market": "mexico", "channel": "investigation discovery", "id": "64"},
    {"market": "mexico", "channel": "el gourmet", "id": "64"},
    {"market": "mexico", "channel": "tnt", "id": "64"},
    {"market": "mexico", "channel": "bandamax", "id": "64"},
    {"market": "mexico", "channel": "a+e", "id": "64"},
    # --- Netherlands ---
    {"market": "netherlands", "channel": "npo 1", "id": "24"},
    {"market": "netherlands", "channel": "npo 2", "id": "24"},
    {"market": "netherlands", "channel": "rtl 4", "id": "24"},
    {"market": "netherlands", "channel": "sbs 6", "id": "24"},
    {"market": "netherlands", "channel": "rtl 7", "id": "24"},
    {"market": "netherlands", "channel": "net 5", "id": "24"},
    {"market": "netherlands", "channel": "veronica", "id": "24"},
    {"market": "netherlands", "channel": "discovery channel", "id": "24"},
    {"market": "netherlands", "channel": "eurosport nl", "id": "24"},
    {"market": "netherlands", "channel": "espn nl", "id": "24"},
    {"market": "netherlands", "channel": "espn 2 nl", "id": "24"},
    {"market": "netherlands", "channel": "espn 3 nl", "id": "24"},
    {"market": "netherlands", "channel": "history", "id": "24"},
    {"market": "netherlands", "channel": "mtv nl", "id": "24"},
    {"market": "netherlands", "channel": "national geographic", "id": "24"},
    {"market": "netherlands", "channel": "rtl z", "id": "24"},
    {"market": "netherlands", "channel": "the learning channel", "id": "24"},
    {"market": "netherlands", "channel": "ziggo sport", "id": "24"},
    {"market": "netherlands", "channel": "ziggo sport 2", "id": "24"},
    {"market": "netherlands", "channel": "ziggo sport 3", "id": "24"},
    {"market": "netherlands", "channel": "npo 3", "id": "24"},
    {"market": "netherlands", "channel": "rtl 5", "id": "24"},
    {"market": "netherlands", "channel": "rtl 8", "id": "24"},
    {"market": "netherlands", "channel": "comedy central nl", "id": "24"},
    {"market": "netherlands", "channel": "bbc nl", "id": "24"},
    {"market": "netherlands", "channel": "star channel", "id": "24"},
    {"market": "netherlands", "channel": "espn 4 nl", "id": "24"},
    {"market": "netherlands", "channel": "investiation discovery", "id": "24"},
    {"market": "netherlands", "channel": "rtl lounge", "id": "24"},
    {"market": "netherlands", "channel": "sbs 9", "id": "24"},
    {"market": "netherlands", "channel": "paramount network", "id": "24"},
    # --- New Zealand ---
    {"market": "new zealand", "channel": "sky sport 6 nzl", "id": "104"},
    {"market": "new zealand", "channel": "sky sport 1 nzl", "id": "104"},
    {"market": "new zealand", "channel": "sky sport 2 nzl", "id": "104"},
    {"market": "new zealand", "channel": "sky sport 4 nzl", "id": "104"},
    {"market": "new zealand", "channel": "sky sport 5 nzl", "id": "104"},
    {"market": "new zealand", "channel": "sky sport premier league nzl", "id": "104"},
    {"market": "new zealand", "channel": "sky sport select nzl", "id": "104"},
    {"market": "new zealand", "channel": "sky sport 3 nzl", "id": "104"},
    {"market": "new zealand", "channel": "sky open nzl", "id": "104"},
    {"market": "new zealand", "channel": "three", "id": "104"},
    {"market": "new zealand", "channel": "tvnz 1", "id": "104"},
    {"market": "new zealand", "channel": "tvnz duke", "id": "104"},
    {"market": "new zealand", "channel": "whakaata maori", "id": "104"},
    {"market": "new zealand", "channel": "tvnz 2", "id": "104"},
    # --- Norway ---
    {"market": "norway", "channel": "nrk 1", "id": "23"},
    {"market": "norway", "channel": "nrk 2", "id": "23"},
    {"market": "norway", "channel": "nrk 3", "id": "23"},
    {"market": "norway", "channel": "tv 2 direkte", "id": "23"},
    {"market": "norway", "channel": "tv 2 zebra", "id": "23"},
    {"market": "norway", "channel": "tv2 livesstil", "id": "23"},
    {"market": "norway", "channel": "tv 2 nyheter", "id": "23"},
    {"market": "norway", "channel": "tv norge", "id": "23"},
    {"market": "norway", "channel": "fem", "id": "23"},
    {"market": "norway", "channel": "rex", "id": "23"},
    {"market": "norway", "channel": "vox", "id": "23"},
    {"market": "norway", "channel": "eurosport 2 no", "id": "23"},
    {"market": "norway", "channel": "eurosport no", "id": "23"},
    {"market": "norway", "channel": "discovery channel", "id": "23"},
    {"market": "norway", "channel": "tlc norge", "id": "23"},
    {"market": "norway", "channel": "tv3 no", "id": "23"},
    {"market": "norway", "channel": "tv3+ no", "id": "23"},
    {"market": "norway", "channel": "tv6", "id": "23"},
    {"market": "norway", "channel": "tv 2 sport premium", "id": "23"},
    {"market": "norway", "channel": "v sport 1 no", "id": "23"},
    {"market": "norway", "channel": "national geographic", "id": "23"},
    {"market": "norway", "channel": "tv 2 sport 1", "id": "23"},
    {"market": "norway", "channel": "tv 2 sport 2", "id": "23"},
    {"market": "norway", "channel": "v sport premier league", "id": "23"},
    {"market": "norway", "channel": "bbc nordic", "id": "23"},
    {"market": "norway", "channel": "investigation discovery", "id": "23"},
    # --- Peru ---
    {"market": "peru", "channel": "canal 4 america television", "id": "101"},
    {"market": "peru", "channel": "atv", "id": "101"},
    {"market": "peru", "channel": "canal n", "id": "101"},
    {"market": "peru", "channel": "gol tv peru", "id": "101"},
    {"market": "peru", "channel": "espn per", "id": "101"},
    {"market": "peru", "channel": "espn 2 per", "id": "101"},
    {"market": "peru", "channel": "espn 3 per", "id": "101"},
    {"market": "peru", "channel": "espn 5 per", "id": "101"},
    {"market": "peru", "channel": "espn 6 per", "id": "101"},
    {"market": "peru", "channel": "espn 7 per", "id": "101"},
    {"market": "peru", "channel": "latina", "id": "101"},
    {"market": "peru", "channel": "panamericana tv", "id": "101"},
    {"market": "peru", "channel": "tv peru", "id": "101"},
    {"market": "peru", "channel": "atv+", "id": "101"},
    {"market": "peru", "channel": "willax tv", "id": "101"},
    # --- Philippines ---
    {"market": "philippines", "channel": "untv 37", "id": "41"},
    {"market": "philippines", "channel": "uaap varsity channel", "id": "41"},
    {"market": "philippines", "channel": "pba rush", "id": "41"},
    {"market": "philippines", "channel": "net25", "id": "41"},
    {"market": "philippines", "channel": "one sports+", "id": "41"},
    {"market": "philippines", "channel": "rptv", "id": "41"},
    {"market": "philippines", "channel": "nba tv philippines", "id": "41"},
    {"market": "philippines", "channel": "abs-cbn news channel", "id": "41"},
    {"market": "philippines", "channel": "kapamilya channel", "id": "41"},
    {"market": "philippines", "channel": "gtv", "id": "41"},
    {"market": "philippines", "channel": "ptv", "id": "41"},
    {"market": "philippines", "channel": "all tv", "id": "41"},
    {"market": "philippines", "channel": "a2z channel 11", "id": "41"},
    {"market": "philippines", "channel": "tv5", "id": "41"},
    {"market": "philippines", "channel": "one news", "id": "41"},
    {"market": "philippines", "channel": "gma-7", "id": "41"},
    {"market": "philippines", "channel": "teleradyo serbisyo", "id": "41"},
    {"market": "philippines", "channel": "one sports", "id": "41"},
    {"market": "philippines", "channel": "ibc", "id": "41"},
    {"market": "philippines", "channel": "one media network", "id": "41"},
    {"market": "philippines", "channel": "cltv 36", "id": "41"},
    {"market": "philippines", "channel": "jeepney tv", "id": "41"},
    {"market": "philippines", "channel": "heart of asia", "id": "41"},
    # --- Poland ---
    {"market": "poland", "channel": "4fun.tv", "id": "26"},
    {"market": "poland", "channel": "4fun dance", "id": "26"},
    {"market": "poland", "channel": "4fun kids", "id": "26"},
    {"market": "poland", "channel": "active family", "id": "26"},
    {"market": "poland", "channel": "ale kino+", "id": "26"},
    {"market": "poland", "channel": "amc", "id": "26"},
    {"market": "poland", "channel": "animal planet hd", "id": "26"},
    {"market": "poland", "channel": "axn black", "id": "26"},
    {"market": "poland", "channel": "axn spin", "id": "26"},
    {"market": "poland", "channel": "bbc brit", "id": "26"},
    {"market": "poland", "channel": "bbc hd", "id": "26"},
    {"market": "poland", "channel": "bbc earth", "id": "26"},
    {"market": "poland", "channel": "bbc lifestyle", "id": "26"},
    {"market": "poland", "channel": "domo+", "id": "26"},
    {"market": "poland", "channel": "canal+ 360 pl", "id": "26"},
    {"market": "poland", "channel": "canal+ sport 3 pl", "id": "26"},
    {"market": "poland", "channel": "canal+ sport 4 pl", "id": "26"},
    {"market": "poland", "channel": "film cafe", "id": "26"},
    {"market": "poland", "channel": "cbs reality", "id": "26"},
    {"market": "poland", "channel": "ci polsat", "id": "26"},
    {"market": "poland", "channel": "comedy central", "id": "26"},
    {"market": "poland", "channel": "discovery", "id": "26"},
    {"market": "poland", "channel": "discovery historia", "id": "26"},
    {"market": "poland", "channel": "discovery life", "id": "26"},
    {"market": "poland", "channel": "discovery science", "id": "26"},
    {"market": "poland", "channel": "novelas +1", "id": "26"},
    {"market": "poland", "channel": "discovery turbo xtra", "id": "26"},
    {"market": "poland", "channel": "e entertainment", "id": "26"},
    {"market": "poland", "channel": "epic drama", "id": "26"},
    {"market": "poland", "channel": "eska tv", "id": "26"},
    {"market": "poland", "channel": "eurosport pl", "id": "26"},
    {"market": "poland", "channel": "eurosport 2 pl", "id": "26"},
    {"market": "poland", "channel": "extreme sports", "id": "26"},
    {"market": "poland", "channel": "food network", "id": "26"},
    {"market": "poland", "channel": "fokus tv", "id": "26"},
    {"market": "poland", "channel": "fox", "id": "26"},
    {"market": "poland", "channel": "fox comedy", "id": "26"},
    {"market": "poland", "channel": "gametoon", "id": "26"},
    {"market": "poland", "channel": "h2", "id": "26"},
    {"market": "poland", "channel": "hgtv hd", "id": "26"},
    {"market": "poland", "channel": "history", "id": "26"},
    {"market": "poland", "channel": "investigation discovery", "id": "26"},
    {"market": "poland", "channel": "metro", "id": "26"},
    {"market": "poland", "channel": "motowizja", "id": "26"},
    {"market": "poland", "channel": "mtv polska", "id": "26"},
    {"market": "poland", "channel": "nat geo people", "id": "26"},
    {"market": "poland", "channel": "nat geo wild", "id": "26"},
    {"market": "poland", "channel": "national geographic", "id": "26"},
    {"market": "poland", "channel": "paramount channel hd", "id": "26"},
    {"market": "poland", "channel": "polo tv", "id": "26"},
    {"market": "poland", "channel": "polonia1", "id": "26"},
    {"market": "poland", "channel": "polsat", "id": "26"},
    {"market": "poland", "channel": "polsat cafe", "id": "26"},
    {"market": "poland", "channel": "polsat film", "id": "26"},
    {"market": "poland", "channel": "polsat games", "id": "26"},
    {"market": "poland", "channel": "polsat music hd", "id": "26"},
    {"market": "poland", "channel": "polsat news 2", "id": "26"},
    {"market": "poland", "channel": "polsat rodzina", "id": "26"},
    {"market": "poland", "channel": "polsat seriale", "id": "26"},
    {"market": "poland", "channel": "polsat sport 3", "id": "26"},
    {"market": "poland", "channel": "polsat viasat explore", "id": "26"},
    {"market": "poland", "channel": "polsat viasat history", "id": "26"},
    {"market": "poland", "channel": "polsat viasat nature", "id": "26"},
    {"market": "poland", "channel": "polsat 2", "id": "26"},
    {"market": "poland", "channel": "scifi universal", "id": "26"},
    {"market": "poland", "channel": "super polsat", "id": "26"},
    {"market": "poland", "channel": "tele5", "id": "26"},
    {"market": "poland", "channel": "telewizja wpolsce.pl", "id": "26"},
    {"market": "poland", "channel": "tlc", "id": "26"},
    {"market": "poland", "channel": "ttv", "id": "26"},
    {"market": "poland", "channel": "tv puls", "id": "26"},
    {"market": "poland", "channel": "tv4 pl", "id": "26"},
    {"market": "poland", "channel": "tvn pl", "id": "26"},
    {"market": "poland", "channel": "tvn fabula", "id": "26"},
    {"market": "poland", "channel": "tvn style", "id": "26"},
    {"market": "poland", "channel": "tvn turbo", "id": "26"},
    {"market": "poland", "channel": "tvn7", "id": "26"},
    {"market": "poland", "channel": "warner tv", "id": "26"},
    {"market": "poland", "channel": "wp", "id": "26"},
    {"market": "poland", "channel": "zoom tv", "id": "26"},
    {"market": "poland", "channel": "13 ulica", "id": "26"},
    {"market": "poland", "channel": "antena tv", "id": "26"},
    {"market": "poland", "channel": "axn white", "id": "26"},
    {"market": "poland", "channel": "kuchnia+", "id": "26"},
    {"market": "poland", "channel": "fight klub", "id": "26"},
    {"market": "poland", "channel": "nowa tv", "id": "26"},
    {"market": "poland", "channel": "polsat sport 1", "id": "26"},
    {"market": "poland", "channel": "polsat sport 2", "id": "26"},
    {"market": "poland", "channel": "puls 2", "id": "26"},
    {"market": "poland", "channel": "travel channel", "id": "26"},
    {"market": "poland", "channel": "tvc", "id": "26"},
    {"market": "poland", "channel": "tvs", "id": "26"},
    {"market": "poland", "channel": "wydarzenia 24", "id": "26"},
    {"market": "poland", "channel": "axn", "id": "26"},
    {"market": "poland", "channel": "bbc cbeebies", "id": "26"},
    {"market": "poland", "channel": "cartoonito", "id": "26"},
    {"market": "poland", "channel": "canal+ premium", "id": "26"},
    {"market": "poland", "channel": "canal+ sport pl", "id": "26"},
    {"market": "poland", "channel": "canal+ sport 2 pl", "id": "26"},
    {"market": "poland", "channel": "canal+ sport 5 pl", "id": "26"},
    {"market": "poland", "channel": "cartoon network", "id": "26"},
    {"market": "poland", "channel": "disco polo music", "id": "26"},
    {"market": "poland", "channel": "disney channel", "id": "26"},
    {"market": "poland", "channel": "disney junior", "id": "26"},
    {"market": "poland", "channel": "disney xd", "id": "26"},
    {"market": "poland", "channel": "eleven sports 1 pl", "id": "26"},
    {"market": "poland", "channel": "eleven sports 2", "id": "26"},
    {"market": "poland", "channel": "home tv", "id": "26"},
    {"market": "poland", "channel": "kino polska", "id": "26"},
    {"market": "poland", "channel": "minimini+", "id": "26"},
    {"market": "poland", "channel": "nickelodeon", "id": "26"},
    {"market": "poland", "channel": "nicktoons", "id": "26"},
    {"market": "poland", "channel": "nick jr", "id": "26"},
    {"market": "poland", "channel": "novelas", "id": "26"},
    {"market": "poland", "channel": "planete+", "id": "26"},
    {"market": "poland", "channel": "polsat doku", "id": "26"},
    {"market": "poland", "channel": "polsat jimjam", "id": "26"},
    {"market": "poland", "channel": "polsat news", "id": "26"},
    {"market": "poland", "channel": "polsat play", "id": "26"},
    {"market": "poland", "channel": "polsat sport fight", "id": "26"},
    {"market": "poland", "channel": "romance tv", "id": "26"},
    {"market": "poland", "channel": "sportklub pol", "id": "26"},
    {"market": "poland", "channel": "stopklatka", "id": "26"},
    {"market": "poland", "channel": "studiomed tv", "id": "26"},
    {"market": "poland", "channel": "sundance tv", "id": "26"},
    {"market": "poland", "channel": "teen nick", "id": "26"},
    {"market": "poland", "channel": "teletoon+", "id": "26"},
    {"market": "poland", "channel": "tv6", "id": "26"},
    {"market": "poland", "channel": "tvn 24", "id": "26"},
    {"market": "poland", "channel": "tvn 24 bis", "id": "26"},
    {"market": "poland", "channel": "tvp dokument", "id": "26"},
    {"market": "poland", "channel": "tvp hd", "id": "26"},
    {"market": "poland", "channel": "tvp historia", "id": "26"},
    {"market": "poland", "channel": "tvp info", "id": "26"},
    {"market": "poland", "channel": "tvp kobieta", "id": "26"},
    {"market": "poland", "channel": "tvp kultura", "id": "26"},
    {"market": "poland", "channel": "tvp nauka", "id": "26"},
    {"market": "poland", "channel": "tvp polonia", "id": "26"},
    {"market": "poland", "channel": "tvp rozrywka", "id": "26"},
    {"market": "poland", "channel": "tvp seriale", "id": "26"},
    {"market": "poland", "channel": "tvp sport", "id": "26"},
    {"market": "poland", "channel": "tvp 1", "id": "26"},
    {"market": "poland", "channel": "tvp 2", "id": "26"},
    {"market": "poland", "channel": "tvp 3", "id": "26"},
    {"market": "poland", "channel": "tv republica", "id": "26"},
    {"market": "poland", "channel": "filmbox premium", "id": "26"},
    {"market": "poland", "channel": "filmax", "id": "26"},
    {"market": "poland", "channel": "kino polska muzyka", "id": "26"},
    {"market": "poland", "channel": "mixtape", "id": "26"},
    {"market": "poland", "channel": "music box polska", "id": "26"},
    {"market": "poland", "channel": "show tv", "id": "26"},
    {"market": "poland", "channel": "stars.tv", "id": "26"},
    {"market": "poland", "channel": "top kids", "id": "26"},
    {"market": "poland", "channel": "xtreme tv", "id": "26"},
    {"market": "poland", "channel": "adventure", "id": "26"},
    {"market": "poland", "channel": "da vinci learning", "id": "26"},
    {"market": "poland", "channel": "eska rock tv", "id": "26"},
    {"market": "poland", "channel": "eska tv extra", "id": "26"},
    {"market": "poland", "channel": "golf zone", "id": "26"},
    {"market": "poland", "channel": "novela tv", "id": "26"},
    {"market": "poland", "channel": "nuta gold", "id": "26"},
    {"market": "poland", "channel": "nuta.tv", "id": "26"},
    {"market": "poland", "channel": "power tv", "id": "26"},
    {"market": "poland", "channel": "ultra tv", "id": "26"},
    {"market": "poland", "channel": "vox music tv", "id": "26"},
    {"market": "poland", "channel": "water planet", "id": "26"},
    {"market": "poland", "channel": "canal+ discovery", "id": "26"},
    {"market": "poland", "channel": "canal+ seriale", "id": "26"},
    {"market": "poland", "channel": "tvp abc", "id": "26"},
    # --- Portugal ---
    {"market": "portugal", "channel": "sic noticias", "id": "25"},
    {"market": "portugal", "channel": "porto canal", "id": "25"},
    {"market": "portugal", "channel": "cmtv", "id": "25"},
    {"market": "portugal", "channel": "rtp noticias", "id": "25"},
    {"market": "portugal", "channel": "sport tv1", "id": "25"},
    {"market": "portugal", "channel": "sport tv+", "id": "25"},
    {"market": "portugal", "channel": "sport tv2", "id": "25"},
    {"market": "portugal", "channel": "canal 11 pt", "id": "25"},
    {"market": "portugal", "channel": "cnn portugal", "id": "25"},
    {"market": "portugal", "channel": "rtp 1", "id": "25"},
    {"market": "portugal", "channel": "rtp 2", "id": "25"},
    {"market": "portugal", "channel": "sic", "id": "25"},
    {"market": "portugal", "channel": "tvi", "id": "25"},
    {"market": "portugal", "channel": "rtp memoria", "id": "25"},
    {"market": "portugal", "channel": "discovery", "id": "25"},
    {"market": "portugal", "channel": "globo", "id": "25"},
    {"market": "portugal", "channel": "tv record", "id": "25"},
    {"market": "portugal", "channel": "news now", "id": "25"},
    {"market": "portugal", "channel": "v+ tvi", "id": "25"},
    {"market": "portugal", "channel": "dazn 1 pt", "id": "25"},
    {"market": "portugal", "channel": "dazn 2 pt", "id": "25"},
    {"market": "portugal", "channel": "dazn 3 pt", "id": "25"},
    {"market": "portugal", "channel": "dazn 4 pt", "id": "25"},
    {"market": "portugal", "channel": "national geographic channel", "id": "25"},
    # --- Puerto Rico ---
    {"market": "puerto rico", "channel": "telemundo pr (wkaq)", "id": "210"},
    {"market": "puerto rico", "channel": "punto 2", "id": "210"},
    {"market": "puerto rico", "channel": "wapa tv", "id": "210"},
    {"market": "puerto rico", "channel": "univision pr (wlii)", "id": "210"},
    {"market": "puerto rico", "channel": "abc 5 pr (wora)", "id": "210"},
    {"market": "puerto rico", "channel": "vive (wora)", "id": "210"},
    {"market": "puerto rico", "channel": "wipr tv (wipr)", "id": "210"},
    {"market": "puerto rico", "channel": "fox pr (wsjx)", "id": "210"},
    {"market": "puerto rico", "channel": "wccv", "id": "210"},
    {"market": "puerto rico", "channel": "widp", "id": "210"},
    {"market": "puerto rico", "channel": "wipr 6.3", "id": "210"},
    {"market": "puerto rico", "channel": "wipr 6.4", "id": "210"},
    {"market": "puerto rico", "channel": "wjpx", "id": "210"},
    {"market": "puerto rico", "channel": "wmtj", "id": "210"},
    {"market": "puerto rico", "channel": "woro 13.1", "id": "210"},
    {"market": "puerto rico", "channel": "wsjp", "id": "210"},
    {"market": "puerto rico", "channel": "wsju 31.1", "id": "210"},
    {"market": "puerto rico", "channel": "wuja", "id": "210"},
    {"market": "puerto rico", "channel": "a+e", "id": "210"},
    {"market": "puerto rico", "channel": "actionmax", "id": "210"},
    {"market": "puerto rico", "channel": "amc", "id": "210"},
    {"market": "puerto rico", "channel": "america teve", "id": "210"},
    {"market": "puerto rico", "channel": "animal planet latin america", "id": "210"},
    {"market": "puerto rico", "channel": "animal planet usa", "id": "210"},
    {"market": "puerto rico", "channel": "atres", "id": "210"},
    {"market": "puerto rico", "channel": "atres series", "id": "210"},
    {"market": "puerto rico", "channel": "axs tv", "id": "210"},
    {"market": "puerto rico", "channel": "az corazon", "id": "210"},
    {"market": "puerto rico", "channel": "az mundo", "id": "210"},
    {"market": "puerto rico", "channel": "bein sports espanol", "id": "210"},
    {"market": "puerto rico", "channel": "boomerang", "id": "210"},
    {"market": "puerto rico", "channel": "bravo", "id": "210"},
    {"market": "puerto rico", "channel": "caracol tv", "id": "210"},
    {"market": "puerto rico", "channel": "cartoon network", "id": "210"},
    {"market": "puerto rico", "channel": "cbs pr", "id": "210"},
    {"market": "puerto rico", "channel": "cine latino", "id": "210"},
    {"market": "puerto rico", "channel": "cinemax", "id": "210"},
    {"market": "puerto rico", "channel": "cnbc", "id": "210"},
    {"market": "puerto rico", "channel": "cnn", "id": "210"},
    {"market": "puerto rico", "channel": "cnn espanol", "id": "210"},
    {"market": "puerto rico", "channel": "cnn headline news", "id": "210"},
    {"market": "puerto rico", "channel": "comedy central", "id": "210"},
    {"market": "puerto rico", "channel": "discovery channel", "id": "210"},
    {"market": "puerto rico", "channel": "discovery kids latin america", "id": "210"},
    {"market": "puerto rico", "channel": "discovery latin america", "id": "210"},
    {"market": "puerto rico", "channel": "disney channel", "id": "210"},
    {"market": "puerto rico", "channel": "disney xd", "id": "210"},
    {"market": "puerto rico", "channel": "e entertainment", "id": "210"},
    {"market": "puerto rico", "channel": "espn pri", "id": "210"},
    {"market": "puerto rico", "channel": "espn deportes pri", "id": "210"},
    {"market": "puerto rico", "channel": "espn news pri", "id": "210"},
    {"market": "puerto rico", "channel": "espn 2 pri", "id": "210"},
    {"market": "puerto rico", "channel": "food network", "id": "210"},
    {"market": "puerto rico", "channel": "foro tv", "id": "210"},
    {"market": "puerto rico", "channel": "fox sports esp", "id": "210"},
    {"market": "puerto rico", "channel": "fox movie channel", "id": "210"},
    {"market": "puerto rico", "channel": "fox sports 1 pri", "id": "210"},
    {"market": "puerto rico", "channel": "freeform", "id": "210"},
    {"market": "puerto rico", "channel": "fxx", "id": "210"},
    {"market": "puerto rico", "channel": "galavision", "id": "210"},
    {"market": "puerto rico", "channel": "gol tv", "id": "210"},
    {"market": "puerto rico", "channel": "golf channel", "id": "210"},
    {"market": "puerto rico", "channel": "hallmark channel", "id": "210"},
    {"market": "puerto rico", "channel": "hbo", "id": "210"},
    {"market": "puerto rico", "channel": "hbo 2", "id": "210"},
    {"market": "puerto rico", "channel": "hbo comedy", "id": "210"},
    {"market": "puerto rico", "channel": "hbo latin america", "id": "210"},
    {"market": "puerto rico", "channel": "hbo signature", "id": "210"},
    {"market": "puerto rico", "channel": "hbo zone", "id": "210"},
    {"market": "puerto rico", "channel": "hgtv", "id": "210"},
    {"market": "puerto rico", "channel": "history", "id": "210"},
    {"market": "puerto rico", "channel": "history en espanol", "id": "210"},
    {"market": "puerto rico", "channel": "hola tv", "id": "210"},
    {"market": "puerto rico", "channel": "ion television", "id": "210"},
    {"market": "puerto rico", "channel": "lifetime", "id": "210"},
    {"market": "puerto rico", "channel": "lifetime movies", "id": "210"},
    {"market": "puerto rico", "channel": "mlb network", "id": "210"},
    {"market": "puerto rico", "channel": "moremax hd", "id": "210"},
    {"market": "puerto rico", "channel": "msnbc", "id": "210"},
    {"market": "puerto rico", "channel": "mtv", "id": "210"},
    {"market": "puerto rico", "channel": "mtv2", "id": "210"},
    {"market": "puerto rico", "channel": "mtv3", "id": "210"},
    {"market": "puerto rico", "channel": "nat geo la (esp)", "id": "210"},
    {"market": "puerto rico", "channel": "national geographic usa", "id": "210"},
    {"market": "puerto rico", "channel": "nba tv", "id": "210"},
    {"market": "puerto rico", "channel": "nbc universo", "id": "210"},
    {"market": "puerto rico", "channel": "nickelodeon", "id": "210"},
    {"market": "puerto rico", "channel": "on directv", "id": "210"},
    {"market": "puerto rico", "channel": "own", "id": "210"},
    {"market": "puerto rico", "channel": "oxygen", "id": "210"},
    {"market": "puerto rico", "channel": "pixl", "id": "210"},
    {"market": "puerto rico", "channel": "qvc", "id": "210"},
    {"market": "puerto rico", "channel": "science channel", "id": "210"},
    {"market": "puerto rico", "channel": "showtime", "id": "210"},
    {"market": "puerto rico", "channel": "sorpresa", "id": "210"},
    {"market": "puerto rico", "channel": "spike", "id": "210"},
    {"market": "puerto rico", "channel": "sci-fi", "id": "210"},
    {"market": "puerto rico", "channel": "tbs", "id": "210"},
    {"market": "puerto rico", "channel": "tcm", "id": "210"},
    {"market": "puerto rico", "channel": "telemundo east coast usa", "id": "210"},
    {"market": "puerto rico", "channel": "teveo", "id": "210"},
    {"market": "puerto rico", "channel": "the weather channel", "id": "210"},
    {"market": "puerto rico", "channel": "thrillermax", "id": "210"},
    {"market": "puerto rico", "channel": "tlc", "id": "210"},
    {"market": "puerto rico", "channel": "tnt", "id": "210"},
    {"market": "puerto rico", "channel": "travel channel", "id": "210"},
    {"market": "puerto rico", "channel": "tru tv", "id": "210"},
    {"market": "puerto rico", "channel": "tv land", "id": "210"},
    {"market": "puerto rico", "channel": "tve internacional", "id": "210"},
    {"market": "puerto rico", "channel": "univision east coast usa", "id": "210"},
    {"market": "puerto rico", "channel": "univision telenovelas", "id": "210"},
    {"market": "puerto rico", "channel": "usa channel", "id": "210"},
    {"market": "puerto rico", "channel": "v-me", "id": "210"},
    {"market": "puerto rico", "channel": "wapa deportes", "id": "210"},
    {"market": "puerto rico", "channel": "azteca east coast usa", "id": "210"},
    {"market": "puerto rico", "channel": "bbc america", "id": "210"},
    {"market": "puerto rico", "channel": "blockbuster studio", "id": "210"},
    {"market": "puerto rico", "channel": "espn classic", "id": "210"},
    {"market": "puerto rico", "channel": "fx", "id": "210"},
    {"market": "puerto rico", "channel": "hbo family", "id": "210"},
    {"market": "puerto rico", "channel": "latele novela network", "id": "210"},
    {"market": "puerto rico", "channel": "nbc sports", "id": "210"},
    {"market": "puerto rico", "channel": "vh1", "id": "210"},
    # --- Romania ---
    {"market": "romania", "channel": "tvr 1", "id": "27"},
    {"market": "romania", "channel": "tvr 2", "id": "27"},
    {"market": "romania", "channel": "pro tv", "id": "27"},
    {"market": "romania", "channel": "antena 1 ro", "id": "27"},
    {"market": "romania", "channel": "acasa", "id": "27"},
    {"market": "romania", "channel": "prima tv", "id": "27"},
    {"market": "romania", "channel": "disney", "id": "27"},
    {"market": "romania", "channel": "discovery", "id": "27"},
    {"market": "romania", "channel": "eurosport ro", "id": "27"},
    {"market": "romania", "channel": "b1 tv", "id": "27"},
    {"market": "romania", "channel": "minimax", "id": "27"},
    {"market": "romania", "channel": "tvr cultural", "id": "27"},
    {"market": "romania", "channel": "national geographic", "id": "27"},
    {"market": "romania", "channel": "etno", "id": "27"},
    {"market": "romania", "channel": "diva", "id": "27"},
    {"market": "romania", "channel": "cartoon network", "id": "27"},
    {"market": "romania", "channel": "national tv", "id": "27"},
    {"market": "romania", "channel": "pro cinema", "id": "27"},
    {"market": "romania", "channel": "n24 plus", "id": "27"},
    {"market": "romania", "channel": "favorit tv", "id": "27"},
    {"market": "romania", "channel": "axn", "id": "27"},
    {"market": "romania", "channel": "antena 3 ro", "id": "27"},
    {"market": "romania", "channel": "u tv", "id": "27"},
    {"market": "romania", "channel": "happy channel", "id": "27"},
    {"market": "romania", "channel": "film cafe", "id": "27"},
    {"market": "romania", "channel": "kanal d", "id": "27"},
    {"market": "romania", "channel": "antena stars", "id": "27"},
    {"market": "romania", "channel": "cbs reality", "id": "27"},
    {"market": "romania", "channel": "national geographic wild", "id": "27"},
    {"market": "romania", "channel": "zu tv", "id": "27"},
    {"market": "romania", "channel": "axn black", "id": "27"},
    {"market": "romania", "channel": "axn white", "id": "27"},
    {"market": "romania", "channel": "digi sport 1 ro", "id": "27"},
    {"market": "romania", "channel": "digi sport 2 ro", "id": "27"},
    {"market": "romania", "channel": "eurosport 2 ro", "id": "27"},
    {"market": "romania", "channel": "tvr 3", "id": "27"},
    {"market": "romania", "channel": "tlc", "id": "27"},
    {"market": "romania", "channel": "cartoonito", "id": "27"},
    {"market": "romania", "channel": "rtv romania", "id": "27"},
    {"market": "romania", "channel": "disney junior", "id": "27"},
    {"market": "romania", "channel": "acasa gold", "id": "27"},
    {"market": "romania", "channel": "prima sport 1", "id": "27"},
    {"market": "romania", "channel": "prima sport 2", "id": "27"},
    {"market": "romania", "channel": "nickelodeon", "id": "27"},
    {"market": "romania", "channel": "comedy central", "id": "27"},
    {"market": "romania", "channel": "amc", "id": "27"},
    {"market": "romania", "channel": "warner tv", "id": "27"},
    {"market": "romania", "channel": "nicktoons", "id": "27"},
    {"market": "romania", "channel": "realitatea plus", "id": "27"},
    {"market": "romania", "channel": "aleph news", "id": "27"},
    {"market": "romania", "channel": "viasat history", "id": "27"},
    {"market": "romania", "channel": "bollywood classic", "id": "27"},
    {"market": "romania", "channel": "jim jam", "id": "27"},
    {"market": "romania", "channel": "kanal d2", "id": "27"},
    {"market": "romania", "channel": "hgtv", "id": "27"},
    {"market": "romania", "channel": "metropola tv", "id": "27"},
    {"market": "romania", "channel": "teennick", "id": "27"},
    {"market": "romania", "channel": "tralala tv", "id": "27"},
    {"market": "romania", "channel": "euronews romania", "id": "27"},
    {"market": "romania", "channel": "prima sport 3", "id": "27"},
    {"market": "romania", "channel": "prima news", "id": "27"},
    {"market": "romania", "channel": "aleph business", "id": "27"},
    {"market": "romania", "channel": "dizi", "id": "27"},
    {"market": "romania", "channel": "nostalgia tv", "id": "27"},
    {"market": "romania", "channel": "food network", "id": "27"},
    {"market": "romania", "channel": "digi 24", "id": "27"},
    {"market": "romania", "channel": "digi sport 3 ro", "id": "27"},
    {"market": "romania", "channel": "tvr info", "id": "27"},
    {"market": "romania", "channel": "viasat kino", "id": "27"},
    {"market": "romania", "channel": "tv paprika", "id": "27"},
    {"market": "romania", "channel": "magic tv", "id": "27"},
    {"market": "romania", "channel": "cinemaraton", "id": "27"},
    {"market": "romania", "channel": "epic drama", "id": "27"},
    {"market": "romania", "channel": "tvr folclor", "id": "27"},
    {"market": "romania", "channel": "bbc first", "id": "27"},
    {"market": "romania", "channel": "film mania", "id": "27"},
    {"market": "romania", "channel": "tvr sport", "id": "27"},
    {"market": "romania", "channel": "history", "id": "27"},
    {"market": "romania", "channel": "viasat explore", "id": "27"},
    {"market": "romania", "channel": "bbc earth", "id": "27"},
    {"market": "romania", "channel": "axn spin", "id": "27"},
    {"market": "romania", "channel": "e entertainment", "id": "27"},
    {"market": "romania", "channel": "nick jr", "id": "27"},
    {"market": "romania", "channel": "kiss tv", "id": "27"},
    {"market": "romania", "channel": "pro arena", "id": "27"},
    {"market": "romania", "channel": "taraf tv", "id": "27"},
    {"market": "romania", "channel": "music channel", "id": "27"},
    {"market": "romania", "channel": "hit music", "id": "27"},
    {"market": "romania", "channel": "digi sport 4 ro", "id": "27"},
    {"market": "romania", "channel": "rock tv", "id": "27"},
    {"market": "romania", "channel": "voyo (www)", "id": "27"},
    {"market": "romania", "channel": "cinestars", "id": "27"},
    # --- Saudi Arabia ---
    {"market": "saudi arabia", "channel": "abu dhabi tv", "id": "72"},
    {"market": "saudi arabia", "channel": "al arabiya", "id": "72"},
    {"market": "saudi arabia", "channel": "al ekhbariya", "id": "72"},
    {"market": "saudi arabia", "channel": "al hadath", "id": "72"},
    {"market": "saudi arabia", "channel": "al jazeera", "id": "72"},
    {"market": "saudi arabia", "channel": "al majd satellite", "id": "72"},
    {"market": "saudi arabia", "channel": "asharq news", "id": "72"},
    {"market": "saudi arabia", "channel": "bein sports 1 hd", "id": "72"},
    {"market": "saudi arabia", "channel": "bein sports 2 hd", "id": "72"},
    {"market": "saudi arabia", "channel": "bein sports 3 hd", "id": "72"},
    {"market": "saudi arabia", "channel": "bein sports 4 hd", "id": "72"},
    {"market": "saudi arabia", "channel": "cartoon network arabic", "id": "72"},
    {"market": "saudi arabia", "channel": "dubai one tv sau", "id": "72"},
    {"market": "saudi arabia", "channel": "dubai tv sau", "id": "72"},
    {"market": "saudi arabia", "channel": "ksa sports 1", "id": "72"},
    {"market": "saudi arabia", "channel": "ksa sports 2", "id": "72"},
    {"market": "saudi arabia", "channel": "mbc 1", "id": "72"},
    {"market": "saudi arabia", "channel": "mbc 2", "id": "72"},
    {"market": "saudi arabia", "channel": "mbc 3", "id": "72"},
    {"market": "saudi arabia", "channel": "mbc 4", "id": "72"},
    {"market": "saudi arabia", "channel": "mbc action", "id": "72"},
    {"market": "saudi arabia", "channel": "mbc bollywood", "id": "72"},
    {"market": "saudi arabia", "channel": "mbc drama", "id": "72"},
    {"market": "saudi arabia", "channel": "mbc max", "id": "72"},
    {"market": "saudi arabia", "channel": "national geographic abu dhabi", "id": "72"},
    {"market": "saudi arabia", "channel": "osn yahala", "id": "72"},
    {"market": "saudi arabia", "channel": "saudi tv1", "id": "72"},
    {"market": "saudi arabia", "channel": "sbc", "id": "72"},
    {"market": "saudi arabia", "channel": "sky news arabia", "id": "72"},
    {"market": "saudi arabia", "channel": "thikrayat", "id": "72"},
    {"market": "saudi arabia", "channel": "zee aflam", "id": "72"},
    {"market": "saudi arabia", "channel": "zee alwan", "id": "72"},
    {"market": "saudi arabia", "channel": "asharq discovery", "id": "72"},
    {"market": "saudi arabia", "channel": "asharq documentary", "id": "72"},
    {"market": "saudi arabia", "channel": "al thaqafeya", "id": "72"},
    {"market": "saudi arabia", "channel": "saudia alaan tv", "id": "72"},
    {"market": "saudi arabia", "channel": "al arabiya business", "id": "72"},
    {"market": "saudi arabia", "channel": "thmanyah 1", "id": "72"},
    {"market": "saudi arabia", "channel": "thmanyah 2", "id": "72"},
    {"market": "saudi arabia", "channel": "wanasah", "id": "72"},
    {"market": "saudi arabia", "channel": "thmanyah 3", "id": "72"},
    # --- Serbia ---
    {"market": "serbia", "channel": "rts 1", "id": "128"},
    {"market": "serbia", "channel": "prva tv srb", "id": "128"},
    {"market": "serbia", "channel": "prva plus", "id": "128"},
    {"market": "serbia", "channel": "prva world", "id": "128"},
    {"market": "serbia", "channel": "prva kick", "id": "128"},
    {"market": "serbia", "channel": "prva life", "id": "128"},
    {"market": "serbia", "channel": "prva files", "id": "128"},
    {"market": "serbia", "channel": "redtv", "id": "128"},
    {"market": "serbia", "channel": "vesti", "id": "128"},
    {"market": "serbia", "channel": "narodna tv", "id": "128"},
    {"market": "serbia", "channel": "pink premium", "id": "128"},
    {"market": "serbia", "channel": "pink family", "id": "128"},
    {"market": "serbia", "channel": "pink movies", "id": "128"},
    {"market": "serbia", "channel": "pink action", "id": "128"},
    {"market": "serbia", "channel": "pink thriller", "id": "128"},
    {"market": "serbia", "channel": "pink western", "id": "128"},
    {"market": "serbia", "channel": "pink crime and mystery", "id": "128"},
    {"market": "serbia", "channel": "pink sci-fi and fantasy", "id": "128"},
    {"market": "serbia", "channel": "pink romance", "id": "128"},
    {"market": "serbia", "channel": "b92", "id": "128"},
    {"market": "serbia", "channel": "nova s", "id": "128"},
    {"market": "serbia", "channel": "nova series", "id": "128"},
    {"market": "serbia", "channel": "star channel", "id": "128"},
    {"market": "serbia", "channel": "star crime", "id": "128"},
    {"market": "serbia", "channel": "star life", "id": "128"},
    {"market": "serbia", "channel": "star movies", "id": "128"},
    {"market": "serbia", "channel": "24 kitchen", "id": "128"},
    {"market": "serbia", "channel": "discovery channel", "id": "128"},
    {"market": "serbia", "channel": "discovery id", "id": "128"},
    {"market": "serbia", "channel": "hgtv", "id": "128"},
    {"market": "serbia", "channel": "tlc", "id": "128"},
    {"market": "serbia", "channel": "diva universal", "id": "128"},
    {"market": "serbia", "channel": "viasat kino", "id": "128"},
    {"market": "serbia", "channel": "arena sport 1p srb", "id": "128"},
    {"market": "serbia", "channel": "arena sport 2p srb", "id": "128"},
    {"market": "serbia", "channel": "kurir tv", "id": "128"},
    {"market": "serbia", "channel": "k1", "id": "128"},
    {"market": "serbia", "channel": "una tv", "id": "128"},
    {"market": "serbia", "channel": "insajder", "id": "128"},
    {"market": "serbia", "channel": "rts 2", "id": "128"},
    {"market": "serbia", "channel": "rts 3 senegal", "id": "128"},
    {"market": "serbia", "channel": "rts drama", "id": "128"},
    {"market": "serbia", "channel": "rts trezor", "id": "128"},
    {"market": "serbia", "channel": "rts zivot", "id": "128"},
    {"market": "serbia", "channel": "rts muzika", "id": "128"},
    {"market": "serbia", "channel": "rts kolo", "id": "128"},
    {"market": "serbia", "channel": "rts poletarac", "id": "128"},
    {"market": "serbia", "channel": "rts nauka", "id": "128"},
    {"market": "serbia", "channel": "rts klasika", "id": "128"},
    {"market": "serbia", "channel": "prva max", "id": "128"},
    {"market": "serbia", "channel": "pink comedy", "id": "128"},
    {"market": "serbia", "channel": "pink serije", "id": "128"},
    {"market": "serbia", "channel": "pink horror", "id": "128"},
    {"market": "serbia", "channel": "n1", "id": "128"},
    {"market": "serbia", "channel": "rtv 1", "id": "128"},
    {"market": "serbia", "channel": "grand kanal", "id": "128"},
    {"market": "serbia", "channel": "cinemania", "id": "128"},
    {"market": "serbia", "channel": "pikaboo", "id": "128"},
    {"market": "serbia", "channel": "cinestar tv", "id": "128"},
    {"market": "serbia", "channel": "cinestar action and thriller", "id": "128"},
    {"market": "serbia", "channel": "national geographic", "id": "128"},
    {"market": "serbia", "channel": "minmax", "id": "128"},
    {"market": "serbia", "channel": "nickelodeon", "id": "128"},
    {"market": "serbia", "channel": "agro tv", "id": "128"},
    {"market": "serbia", "channel": "superstar tv", "id": "128"},
    {"market": "serbia", "channel": "superstar 2 tv", "id": "128"},
    {"market": "serbia", "channel": "superstar 3", "id": "128"},
    {"market": "serbia", "channel": "arena sport 3p srb", "id": "128"},
    {"market": "serbia", "channel": "arena 4 premium", "id": "128"},
    {"market": "serbia", "channel": "arena 5 premium", "id": "128"},
    {"market": "serbia", "channel": "balkan trip", "id": "128"},
    {"market": "serbia", "channel": "toxic tv", "id": "128"},
    {"market": "serbia", "channel": "euronews srbija", "id": "128"},
    {"market": "serbia", "channel": "dox tv", "id": "128"},
    {"market": "serbia", "channel": "klasik tv", "id": "128"},
    {"market": "serbia", "channel": "dexy tv", "id": "128"},
    {"market": "serbia", "channel": "kazbuka", "id": "128"},
    {"market": "serbia", "channel": "tv doktor", "id": "128"},
    {"market": "serbia", "channel": "nick jr", "id": "128"},
    {"market": "serbia", "channel": "blic tv", "id": "128"},
    {"market": "serbia", "channel": "informer tv", "id": "128"},
    {"market": "serbia", "channel": "newsmax balkans", "id": "128"},
    {"market": "serbia", "channel": "pink tv", "id": "128"},
    {"market": "serbia", "channel": "pink classic", "id": "128"},
    {"market": "serbia", "channel": "arena fight srb", "id": "128"},
    {"market": "serbia", "channel": "pink folk 1", "id": "128"},
    # --- Slovenia ---
    {"market": "slovenia", "channel": "24 kitchen", "id": "31"},
    {"market": "slovenia", "channel": "animal planet", "id": "31"},
    {"market": "slovenia", "channel": "arena sport 1 premium svn", "id": "31"},
    {"market": "slovenia", "channel": "brio", "id": "31"},
    {"market": "slovenia", "channel": "cinestar tv 1", "id": "31"},
    {"market": "slovenia", "channel": "cinestar tv action", "id": "31"},
    {"market": "slovenia", "channel": "cinestar tv fantasy", "id": "31"},
    {"market": "slovenia", "channel": "discovery channel", "id": "31"},
    {"market": "slovenia", "channel": "diva", "id": "31"},
    {"market": "slovenia", "channel": "eurosport si", "id": "31"},
    {"market": "slovenia", "channel": "hgtv", "id": "31"},
    {"market": "slovenia", "channel": "id", "id": "31"},
    {"market": "slovenia", "channel": "kanal a slo", "id": "31"},
    {"market": "slovenia", "channel": "kino", "id": "31"},
    {"market": "slovenia", "channel": "national geographic", "id": "31"},
    {"market": "slovenia", "channel": "pickbox tv", "id": "31"},
    {"market": "slovenia", "channel": "planet tv", "id": "31"},
    {"market": "slovenia", "channel": "planet 2", "id": "31"},
    {"market": "slovenia", "channel": "planet eva", "id": "31"},
    {"market": "slovenia", "channel": "pop tv", "id": "31"},
    {"market": "slovenia", "channel": "sportklub 1 svn", "id": "31"},
    {"market": "slovenia", "channel": "sportklub 2 svn", "id": "31"},
    {"market": "slovenia", "channel": "sportklub 3 svn", "id": "31"},
    {"market": "slovenia", "channel": "sport tv1 slovenia", "id": "31"},
    {"market": "slovenia", "channel": "star channel", "id": "31"},
    {"market": "slovenia", "channel": "star crime", "id": "31"},
    {"market": "slovenia", "channel": "star life", "id": "31"},
    {"market": "slovenia", "channel": "star movies", "id": "31"},
    {"market": "slovenia", "channel": "tlc", "id": "31"},
    {"market": "slovenia", "channel": "travel channel", "id": "31"},
    {"market": "slovenia", "channel": "viasat kino", "id": "31"},
    {"market": "slovenia", "channel": "viasat explore", "id": "31"},
    {"market": "slovenia", "channel": "viasat history", "id": "31"},
    {"market": "slovenia", "channel": "arena sport 1 svn", "id": "31"},
    {"market": "slovenia", "channel": "nick jr.", "id": "31"},
    {"market": "slovenia", "channel": "nickelodeon", "id": "31"},
    {"market": "slovenia", "channel": "rtv slo 1", "id": "31"},
    {"market": "slovenia", "channel": "amc", "id": "31"},
    {"market": "slovenia", "channel": "oto", "id": "31"},
    {"market": "slovenia", "channel": "rtv slo 2", "id": "31"},
    # --- South Africa ---
    {"market": "south africa", "channel": "bbc world news", "id": "39"},
    {"market": "south africa", "channel": "channel o", "id": "39"},
    {"market": "south africa", "channel": "cnn international", "id": "39"},
    {"market": "south africa", "channel": "e.tv", "id": "39"},
    {"market": "south africa", "channel": "enca", "id": "39"},
    {"market": "south africa", "channel": "eextra", "id": "39"},
    {"market": "south africa", "channel": "emovies", "id": "39"},
    {"market": "south africa", "channel": "ereality", "id": "39"},
    {"market": "south africa", "channel": "mzansi magic", "id": "39"},
    {"market": "south africa", "channel": "mzansi magic music", "id": "39"},
    {"market": "south africa", "channel": "mzansi wethu", "id": "39"},
    {"market": "south africa", "channel": "national geographic channel", "id": "39"},
    {"market": "south africa", "channel": "natgeo wild", "id": "39"},
    {"market": "south africa", "channel": "sky news", "id": "39"},
    {"market": "south africa", "channel": "supersport blitz za", "id": "39"},
    {"market": "south africa", "channel": "supersport grandstand za", "id": "39"},
    {"market": "south africa", "channel": "supersport psl za", "id": "39"},
    {"market": "south africa", "channel": "supersport premier league za", "id": "39"},
    {"market": "south africa", "channel": "supersport laliga za", "id": "39"},
    {"market": "south africa", "channel": "supersport football za", "id": "39"},
    {"market": "south africa", "channel": "supersport variety 1 za", "id": "39"},
    {"market": "south africa", "channel": "supersport variety 2 za", "id": "39"},
    {"market": "south africa", "channel": "supersport variety 3 za", "id": "39"},
    {"market": "south africa", "channel": "supersport variety 4 za", "id": "39"},
    {"market": "south africa", "channel": "supersport rugby za", "id": "39"},
    {"market": "south africa", "channel": "supersport cricket za", "id": "39"},
    {"market": "south africa", "channel": "supersport golf za", "id": "39"},
    {"market": "south africa", "channel": "supersport tennis za", "id": "39"},
    {"market": "south africa", "channel": "trace urban", "id": "39"},
    {"market": "south africa", "channel": "trace gospel", "id": "39"},
    {"market": "south africa", "channel": "via", "id": "39"},
    {"market": "south africa", "channel": "supersport schools", "id": "39"},
    {"market": "south africa", "channel": "racing 240", "id": "39"},
    {"market": "south africa", "channel": "bet", "id": "39"},
    {"market": "south africa", "channel": "bbc brit", "id": "39"},
    {"market": "south africa", "channel": "bbc earth", "id": "39"},
    {"market": "south africa", "channel": "bbc lifestyle", "id": "39"},
    {"market": "south africa", "channel": "cartoonito", "id": "39"},
    {"market": "south africa", "channel": "cape town tv", "id": "39"},
    {"market": "south africa", "channel": "cartoon network", "id": "39"},
    {"market": "south africa", "channel": "cbs reality", "id": "39"},
    {"market": "south africa", "channel": "cbeebies", "id": "39"},
    {"market": "south africa", "channel": "cbs justice", "id": "39"},
    {"market": "south africa", "channel": "comedy central", "id": "39"},
    {"market": "south africa", "channel": "curiosity channel", "id": "39"},
    {"market": "south africa", "channel": "dbe tv", "id": "39"},
    {"market": "south africa", "channel": "discovery channel", "id": "39"},
    {"market": "south africa", "channel": "discovery family", "id": "39"},
    {"market": "south africa", "channel": "disney channel", "id": "39"},
    {"market": "south africa", "channel": "disney junior", "id": "39"},
    {"market": "south africa", "channel": "dumisa", "id": "39"},
    {"market": "south africa", "channel": "eplesier", "id": "39"},
    {"market": "south africa", "channel": "e entertainment", "id": "39"},
    {"market": "south africa", "channel": "espn 2 za", "id": "39"},
    {"market": "south africa", "channel": "food network", "id": "39"},
    {"market": "south africa", "channel": "history", "id": "39"},
    {"market": "south africa", "channel": "hgtv", "id": "39"},
    {"market": "south africa", "channel": "id xtra", "id": "39"},
    {"market": "south africa", "channel": "ignition tv", "id": "39"},
    {"market": "south africa", "channel": "kix", "id": "39"},
    {"market": "south africa", "channel": "kyknet nou", "id": "39"},
    {"market": "south africa", "channel": "mpuma kapa tv", "id": "39"},
    {"market": "south africa", "channel": "m-net movies 1", "id": "39"},
    {"market": "south africa", "channel": "m-net movies 2", "id": "39"},
    {"market": "south africa", "channel": "m-net movies 3", "id": "39"},
    {"market": "south africa", "channel": "m-net movies 4", "id": "39"},
    {"market": "south africa", "channel": "mtv", "id": "39"},
    {"market": "south africa", "channel": "mzansi bioskop", "id": "39"},
    {"market": "south africa", "channel": "moja love", "id": "39"},
    {"market": "south africa", "channel": "moja 9.9", "id": "39"},
    {"market": "south africa", "channel": "newzroom afrika", "id": "39"},
    {"market": "south africa", "channel": "nick toons", "id": "39"},
    {"market": "south africa", "channel": "nick junior", "id": "39"},
    {"market": "south africa", "channel": "nickelodeon", "id": "39"},
    {"market": "south africa", "channel": "one gospel", "id": "39"},
    {"market": "south africa", "channel": "real time", "id": "39"},
    {"market": "south africa", "channel": "rok", "id": "39"},
    {"market": "south africa", "channel": "sabc1", "id": "39"},
    {"market": "south africa", "channel": "sabc education", "id": "39"},
    {"market": "south africa", "channel": "sabc news channel", "id": "39"},
    {"market": "south africa", "channel": "sabc sport", "id": "39"},
    {"market": "south africa", "channel": "sa music", "id": "39"},
    {"market": "south africa", "channel": "soweto tv", "id": "39"},
    {"market": "south africa", "channel": "star life", "id": "39"},
    {"market": "south africa", "channel": "studio universal", "id": "39"},
    {"market": "south africa", "channel": "tbn africa", "id": "39"},
    {"market": "south africa", "channel": "tlc entertainment", "id": "39"},
    {"market": "south africa", "channel": "the home channel", "id": "39"},
    {"market": "south africa", "channel": "the home channel+", "id": "39"},
    {"market": "south africa", "channel": "telemundo", "id": "39"},
    {"market": "south africa", "channel": "peoples weather channel", "id": "39"},
    {"market": "south africa", "channel": "travel channel", "id": "39"},
    {"market": "south africa", "channel": "universal channel", "id": "39"},
    {"market": "south africa", "channel": "wildearth", "id": "39"},
    {"market": "south africa", "channel": "1kzn tv", "id": "39"},
    {"market": "south africa", "channel": "zee world", "id": "39"},
    {"market": "south africa", "channel": "zee one", "id": "39"},
    {"market": "south africa", "channel": "bbc uktv", "id": "39"},
    {"market": "south africa", "channel": "dreamworks", "id": "39"},
    {"market": "south africa", "channel": "sabc lehae", "id": "39"},
    {"market": "south africa", "channel": "africa magic epic movies", "id": "39"},
    {"market": "south africa", "channel": "eseries", "id": "39"},
    {"market": "south africa", "channel": "etoons", "id": "39"},
    {"market": "south africa", "channel": "espn za", "id": "39"},
    {"market": "south africa", "channel": "kyknet", "id": "39"},
    {"market": "south africa", "channel": "kyknet + kie", "id": "39"},
    {"market": "south africa", "channel": "kyknet lekker", "id": "39"},
    {"market": "south africa", "channel": "m-net", "id": "39"},
    {"market": "south africa", "channel": "mtv base", "id": "39"},
    {"market": "south africa", "channel": "sabc2", "id": "39"},
    {"market": "south africa", "channel": "sabc3", "id": "39"},
    {"market": "south africa", "channel": "supersport action za", "id": "39"},
    {"market": "south africa", "channel": "supersport wwe za", "id": "39"},
    {"market": "south africa", "channel": "supersport motorsport za", "id": "39"},
    {"market": "south africa", "channel": "tnt africa", "id": "39"},
    {"market": "south africa", "channel": "movie room", "id": "39"},
    {"market": "south africa", "channel": "switchd on channel 109", "id": "39"},
    {"market": "south africa", "channel": "switchd on channel 110", "id": "39"},
    {"market": "south africa", "channel": "trace africa", "id": "39"},
    # --- South Korea ---
    {"market": "south korea", "channel": "cpbc", "id": "86"},
    {"market": "south korea", "channel": "national assembly tv", "id": "86"},
    {"market": "south korea", "channel": "daekyo newifplus", "id": "86"},
    {"market": "south korea", "channel": "ena drama", "id": "86"},
    {"market": "south korea", "channel": "real tv", "id": "86"},
    {"market": "south korea", "channel": "mountain tv", "id": "86"},
    {"market": "south korea", "channel": "billiards tv", "id": "86"},
    {"market": "south korea", "channel": "living sports tv", "id": "86"},
    {"market": "south korea", "channel": "anione", "id": "86"},
    {"market": "south korea", "channel": "aniplus tv", "id": "86"},
    {"market": "south korea", "channel": "kids tv", "id": "86"},
    {"market": "south korea", "channel": "mplex", "id": "86"},
    {"market": "south korea", "channel": "yonhab news tv", "id": "86"},
    {"market": "south korea", "channel": "zhounghwa tv", "id": "86"},
    {"market": "south korea", "channel": "channel china", "id": "86"},
    {"market": "south korea", "channel": "channel a", "id": "86"},
    {"market": "south korea", "channel": "channel a plus", "id": "86"},
    {"market": "south korea", "channel": "ocn movies", "id": "86"},
    {"market": "south korea", "channel": "channel w", "id": "86"},
    {"market": "south korea", "channel": "cartoon network", "id": "86"},
    {"market": "south korea", "channel": "comedy tv", "id": "86"},
    {"market": "south korea", "channel": "i show", "id": "86"},
    {"market": "south korea", "channel": "yonhapnews", "id": "86"},
    {"market": "south korea", "channel": "bravokids", "id": "86"},
    {"market": "south korea", "channel": "korea business news tv", "id": "86"},
    {"market": "south korea", "channel": "health medi tv", "id": "86"},
    {"market": "south korea", "channel": "channel u", "id": "86"},
    {"market": "south korea", "channel": "animax", "id": "86"},
    {"market": "south korea", "channel": "cartoonito", "id": "86"},
    {"market": "south korea", "channel": "cbs", "id": "86"},
    {"market": "south korea", "channel": "cgn", "id": "86"},
    {"market": "south korea", "channel": "ch view", "id": "86"},
    {"market": "south korea", "channel": "channel j", "id": "86"},
    {"market": "south korea", "channel": "ching", "id": "86"},
    {"market": "south korea", "channel": "cinef", "id": "86"},
    {"market": "south korea", "channel": "cmc family entertainment tv", "id": "86"},
    {"market": "south korea", "channel": "cntv", "id": "86"},
    {"market": "south korea", "channel": "storytv", "id": "86"},
    {"market": "south korea", "channel": "cts", "id": "86"},
    {"market": "south korea", "channel": "tv chosun 2", "id": "86"},
    {"market": "south korea", "channel": "c channel", "id": "86"},
    {"market": "south korea", "channel": "discovery tv", "id": "86"},
    {"market": "south korea", "channel": "d-one", "id": "86"},
    {"market": "south korea", "channel": "dramacube", "id": "86"},
    {"market": "south korea", "channel": "dramax", "id": "86"},
    {"market": "south korea", "channel": "ebs kids", "id": "86"},
    {"market": "south korea", "channel": "edgetv", "id": "86"},
    {"market": "south korea", "channel": "e channel", "id": "86"},
    {"market": "south korea", "channel": "e like", "id": "86"},
    {"market": "south korea", "channel": "ch.now", "id": "86"},
    {"market": "south korea", "channel": "ch.ever", "id": "86"},
    {"market": "south korea", "channel": "ftv", "id": "86"},
    {"market": "south korea", "channel": "fun tv", "id": "86"},
    {"market": "south korea", "channel": "mx", "id": "86"},
    {"market": "south korea", "channel": "good tv", "id": "86"},
    {"market": "south korea", "channel": "gtv", "id": "86"},
    {"market": "south korea", "channel": "hq+", "id": "86"},
    {"market": "south korea", "channel": "jei talent tv", "id": "86"},
    {"market": "south korea", "channel": "jtbc", "id": "86"},
    {"market": "south korea", "channel": "jtbc 2", "id": "86"},
    {"market": "south korea", "channel": "kbs joy", "id": "86"},
    {"market": "south korea", "channel": "kbs story", "id": "86"},
    {"market": "south korea", "channel": "kbs south korea", "id": "86"},
    {"market": "south korea", "channel": "kbs2 south korea", "id": "86"},
    {"market": "south korea", "channel": "kbs life", "id": "86"},
    {"market": "south korea", "channel": "kbs n sports", "id": "86"},
    {"market": "south korea", "channel": "kbs drama", "id": "86"},
    {"market": "south korea", "channel": "k star", "id": "86"},
    {"market": "south korea", "channel": "ktv", "id": "86"},
    {"market": "south korea", "channel": "tv baduk", "id": "86"},
    {"market": "south korea", "channel": "i play", "id": "86"},
    {"market": "south korea", "channel": "mbc south korea", "id": "86"},
    {"market": "south korea", "channel": "mbc m", "id": "86"},
    {"market": "south korea", "channel": "mbc sports+", "id": "86"},
    {"market": "south korea", "channel": "mbc on", "id": "86"},
    {"market": "south korea", "channel": "mbc drama net", "id": "86"},
    {"market": "south korea", "channel": "mbn", "id": "86"},
    {"market": "south korea", "channel": "mbn plus", "id": "86"},
    {"market": "south korea", "channel": "mnet", "id": "86"},
    {"market": "south korea", "channel": "mtn", "id": "86"},
    {"market": "south korea", "channel": "sbs golf 2", "id": "86"},
    {"market": "south korea", "channel": "obs", "id": "86"},
    {"market": "south korea", "channel": "ocn", "id": "86"},
    {"market": "south korea", "channel": "ogn", "id": "86"},
    {"market": "south korea", "channel": "tvn drama", "id": "86"},
    {"market": "south korea", "channel": "ont", "id": "86"},
    {"market": "south korea", "channel": "sbs south korea", "id": "86"},
    {"market": "south korea", "channel": "sbs biz", "id": "86"},
    {"market": "south korea", "channel": "sbs golf", "id": "86"},
    {"market": "south korea", "channel": "asia m", "id": "86"},
    {"market": "south korea", "channel": "sbs plus", "id": "86"},
    {"market": "south korea", "channel": "sbs sports", "id": "86"},
    {"market": "south korea", "channel": "screen", "id": "86"},
    {"market": "south korea", "channel": "kbs kids", "id": "86"},
    {"market": "south korea", "channel": "ena", "id": "86"},
    {"market": "south korea", "channel": "ena play", "id": "86"},
    {"market": "south korea", "channel": "once", "id": "86"},
    {"market": "south korea", "channel": "olife", "id": "86"},
    {"market": "south korea", "channel": "smiletv plus", "id": "86"},
    {"market": "south korea", "channel": "spo tv1", "id": "86"},
    {"market": "south korea", "channel": "spotv prime", "id": "86"},
    {"market": "south korea", "channel": "spotv prime 2", "id": "86"},
    {"market": "south korea", "channel": "spotv golf and health", "id": "86"},
    {"market": "south korea", "channel": "spo tv2", "id": "86"},
    {"market": "south korea", "channel": "ocn movies 2", "id": "86"},
    {"market": "south korea", "channel": "golf and pba", "id": "86"},
    {"market": "south korea", "channel": "the movie", "id": "86"},
    {"market": "south korea", "channel": "tooniverse", "id": "86"},
    {"market": "south korea", "channel": "ena story", "id": "86"},
    {"market": "south korea", "channel": "tvasia plus", "id": "86"},
    {"market": "south korea", "channel": "tvn south korea", "id": "86"},
    {"market": "south korea", "channel": "tv chosun", "id": "86"},
    {"market": "south korea", "channel": "tvn show", "id": "86"},
    {"market": "south korea", "channel": "ytn", "id": "86"},
    {"market": "south korea", "channel": "kfn", "id": "86"},
    {"market": "south korea", "channel": "anibox", "id": "86"},
    {"market": "south korea", "channel": "nxt", "id": "86"},
    {"market": "south korea", "channel": "jtbc golf", "id": "86"},
    {"market": "south korea", "channel": "mbc every1", "id": "86"},
    {"market": "south korea", "channel": "sbs fune", "id": "86"},
    {"market": "south korea", "channel": "soop", "id": "86"},
    {"market": "south korea", "channel": "jtbc 4", "id": "86"},
    {"market": "south korea", "channel": "sbs life", "id": "86"},
    {"market": "south korea", "channel": "spotv prime +", "id": "86"},
    {"market": "south korea", "channel": "thelife2", "id": "86"},
    {"market": "south korea", "channel": "the life", "id": "86"},
    {"market": "south korea", "channel": "tv chosun 3", "id": "86"},
    {"market": "south korea", "channel": "tvn story", "id": "86"},
    {"market": "south korea", "channel": "lifetime", "id": "86"},
    {"market": "south korea", "channel": "poyo tv", "id": "86"},
    {"market": "south korea", "channel": "cinema heaven", "id": "86"},
    {"market": "south korea", "channel": "x one", "id": "86"},
    {"market": "south korea", "channel": "channel s", "id": "86"},
    {"market": "south korea", "channel": "channel s plus", "id": "86"},
    {"market": "south korea", "channel": "history", "id": "86"},
    {"market": "south korea", "channel": "ebs", "id": "86"},
    {"market": "south korea", "channel": "ib sports", "id": "86"},
    {"market": "south korea", "channel": "jtbc golf and sports", "id": "86"},
    {"market": "south korea", "channel": "ena sports", "id": "86"},
    {"market": "south korea", "channel": "tvn sports", "id": "86"},
    {"market": "south korea", "channel": "maxports", "id": "86"},
    {"market": "south korea", "channel": "coupang play (www)", "id": "86"},
    {"market": "south korea", "channel": "spotv k", "id": "86"},
    # --- Spain ---
    {"market": "spain", "channel": "tve 2", "id": "15"},
    {"market": "spain", "channel": "telecinco", "id": "15"},
    {"market": "spain", "channel": "antena 3", "id": "15"},
    {"market": "spain", "channel": "canal sur", "id": "15"},
    {"market": "spain", "channel": "tv3", "id": "15"},
    {"market": "spain", "channel": "etb 1", "id": "15"},
    {"market": "spain", "channel": "etb 2", "id": "15"},
    {"market": "spain", "channel": "tvg", "id": "15"},
    {"market": "spain", "channel": "telemadrid", "id": "15"},
    {"market": "spain", "channel": "canal sur andalucia", "id": "15"},
    {"market": "spain", "channel": "tv3 cat", "id": "15"},
    {"market": "spain", "channel": "tv canaria", "id": "15"},
    {"market": "spain", "channel": "etb 4", "id": "15"},
    {"market": "spain", "channel": "cmm tv", "id": "15"},
    {"market": "spain", "channel": "cuatro", "id": "15"},
    {"market": "spain", "channel": "etb 3", "id": "15"},
    {"market": "spain", "channel": "la sexta", "id": "15"},
    {"market": "spain", "channel": "la otra", "id": "15"},
    {"market": "spain", "channel": "tpa 2", "id": "15"},
    {"market": "spain", "channel": "aragon tv", "id": "15"},
    {"market": "spain", "channel": "tv asturias", "id": "15"},
    {"market": "spain", "channel": "ib3", "id": "15"},
    {"market": "spain", "channel": "la siete", "id": "15"},
    {"market": "spain", "channel": "tvg 2", "id": "15"},
    {"market": "spain", "channel": "7 region de murcia", "id": "15"},
    {"market": "spain", "channel": "sx3", "id": "15"},
    {"market": "spain", "channel": "tv mediterraneo", "id": "15"},
    {"market": "spain", "channel": "andalucia television", "id": "15"},
    {"market": "spain", "channel": "a punt", "id": "15"},
    {"market": "spain", "channel": "btv beteve", "id": "15"},
    {"market": "spain", "channel": "canal 24 horas", "id": "15"},
    {"market": "spain", "channel": "3catinfo", "id": "15"},
    {"market": "spain", "channel": "neox", "id": "15"},
    {"market": "spain", "channel": "nova", "id": "15"},
    {"market": "spain", "channel": "axn", "id": "15"},
    {"market": "spain", "channel": "amc break", "id": "15"},
    {"market": "spain", "channel": "historia", "id": "15"},
    {"market": "spain", "channel": "accion por m+", "id": "15"},
    {"market": "spain", "channel": "comedia por m+", "id": "15"},
    {"market": "spain", "channel": "drama por m+", "id": "15"},
    {"market": "spain", "channel": "deportes por m+", "id": "15"},
    {"market": "spain", "channel": "calle 13", "id": "15"},
    {"market": "spain", "channel": "canal cocina", "id": "15"},
    {"market": "spain", "channel": "canal hollywood", "id": "15"},
    {"market": "spain", "channel": "caza y pesca", "id": "15"},
    {"market": "spain", "channel": "sundance tv", "id": "15"},
    {"market": "spain", "channel": "clan", "id": "15"},
    {"market": "spain", "channel": "cosmopolitan tv", "id": "15"},
    {"market": "spain", "channel": "dark", "id": "15"},
    {"market": "spain", "channel": "cine espanol por m+", "id": "15"},
    {"market": "spain", "channel": "decasa", "id": "15"},
    {"market": "spain", "channel": "discovery", "id": "15"},
    {"market": "spain", "channel": "eurosport spain", "id": "15"},
    {"market": "spain", "channel": "xtrm", "id": "15"},
    {"market": "spain", "channel": "fdf", "id": "15"},
    {"market": "spain", "channel": "star channel", "id": "15"},
    {"market": "spain", "channel": "golf por m+", "id": "15"},
    {"market": "spain", "channel": "mtv", "id": "15"},
    {"market": "spain", "channel": "national geographic", "id": "15"},
    {"market": "spain", "channel": "nickelodeon", "id": "15"},
    {"market": "spain", "channel": "odisea tv", "id": "15"},
    {"market": "spain", "channel": "comedy central", "id": "15"},
    {"market": "spain", "channel": "disney junior", "id": "15"},
    {"market": "spain", "channel": "syfy", "id": "15"},
    {"market": "spain", "channel": "somos", "id": "15"},
    {"market": "spain", "channel": "tcm", "id": "15"},
    {"market": "spain", "channel": "teledeporte", "id": "15"},
    {"market": "spain", "channel": "warner tv", "id": "15"},
    {"market": "spain", "channel": "boing", "id": "15"},
    {"market": "spain", "channel": "trece", "id": "15"},
    {"market": "spain", "channel": "esport3", "id": "15"},
    {"market": "spain", "channel": "nick jr", "id": "15"},
    {"market": "spain", "channel": "amc crime", "id": "15"},
    {"market": "spain", "channel": "nat geo wild", "id": "15"},
    {"market": "spain", "channel": "divinity", "id": "15"},
    {"market": "spain", "channel": "energy", "id": "15"},
    {"market": "spain", "channel": "dmax es", "id": "15"},
    {"market": "spain", "channel": "paramount network", "id": "15"},
    {"market": "spain", "channel": "tcm +1", "id": "15"},
    {"market": "spain", "channel": "amc", "id": "15"},
    {"market": "spain", "channel": "mega", "id": "15"},
    {"market": "spain", "channel": "eurosport 2 es", "id": "15"},
    {"market": "spain", "channel": "atreseries", "id": "15"},
    {"market": "spain", "channel": "be mad tv", "id": "15"},
    {"market": "spain", "channel": "ten", "id": "15"},
    {"market": "spain", "channel": "real madrid tv", "id": "15"},
    {"market": "spain", "channel": "dkiss", "id": "15"},
    {"market": "spain", "channel": "bom", "id": "15"},
    {"market": "spain", "channel": "liga de campeones por m+", "id": "15"},
    {"market": "spain", "channel": "vamos por m+", "id": "15"},
    {"market": "spain", "channel": "laligatv por m+", "id": "15"},
    {"market": "spain", "channel": "telemadrid international", "id": "15"},
    {"market": "spain", "channel": "selekt", "id": "15"},
    {"market": "spain", "channel": "dazn 2 es", "id": "15"},
    {"market": "spain", "channel": "dazn f1 es", "id": "15"},
    {"market": "spain", "channel": "estrenos por m+", "id": "15"},
    {"market": "spain", "channel": "clasicos por m+", "id": "15"},
    {"market": "spain", "channel": "ellas v", "id": "15"},
    {"market": "spain", "channel": "dazn laliga", "id": "15"},
    {"market": "spain", "channel": "laliga tv hypermotion", "id": "15"},
    {"market": "spain", "channel": "bbc earth", "id": "15"},
    {"market": "spain", "channel": "vintv", "id": "15"},
    {"market": "spain", "channel": "ubeat", "id": "15"},
    {"market": "spain", "channel": "buen viaje", "id": "15"},
    {"market": "spain", "channel": "axn movies", "id": "15"},
    {"market": "spain", "channel": "movistar plus+", "id": "15"},
    {"market": "spain", "channel": "originales poer m+", "id": "15"},
    {"market": "spain", "channel": "documentales por m+", "id": "15"},
    {"market": "spain", "channel": "indie por m+", "id": "15"},
    {"market": "spain", "channel": "navidad por m+", "id": "15"},
    {"market": "spain", "channel": "squirrel", "id": "15"},
    {"market": "spain", "channel": "hits por m+", "id": "15"},
    {"market": "spain", "channel": "gol play", "id": "15"},
    {"market": "spain", "channel": "primera federacion", "id": "15"},
    {"market": "spain", "channel": "vamos 2 por m+", "id": "15"},
    {"market": "spain", "channel": "tve 1", "id": "15"},
    {"market": "spain", "channel": "la 8", "id": "15"},
    {"market": "spain", "channel": "8tv madrid", "id": "15"},
    {"market": "spain", "channel": "liga de campeones 2 por m+", "id": "15"},
    {"market": "spain", "channel": "dazn 1 es", "id": "15"},
    {"market": "spain", "channel": "liga de campeones 3 por m+", "id": "15"},
    {"market": "spain", "channel": "deportes 2 por m+", "id": "15"},
    {"market": "spain", "channel": "dazn 3 es", "id": "15"},
    {"market": "spain", "channel": "dazn 4 es", "id": "15"},
    {"market": "spain", "channel": "laligatv 2 por m+", "id": "15"},
    {"market": "spain", "channel": "laliga tv hypermotion 2", "id": "15"},
    {"market": "spain", "channel": "dazn laliga 2", "id": "15"},
    {"market": "spain", "channel": "golf 2 por m+", "id": "15"},
    {"market": "spain", "channel": "laliga tv hypermotion 3", "id": "15"},
    {"market": "spain", "channel": "laligatv 3 por m+", "id": "15"},
    {"market": "spain", "channel": "en juego por m+", "id": "15"},
    {"market": "spain", "channel": "laligatv 4 por m+", "id": "15"},
    # --- Sweden ---
    {"market": "sweden", "channel": "svt 1", "id": "29"},
    {"market": "sweden", "channel": "discovery", "id": "29"},
    {"market": "sweden", "channel": "kanal 5 se", "id": "29"},
    {"market": "sweden", "channel": "tv3 se", "id": "29"},
    {"market": "sweden", "channel": "tv4 se", "id": "29"},
    {"market": "sweden", "channel": "kanal 9 se", "id": "29"},
    {"market": "sweden", "channel": "tv sjuan", "id": "29"},
    {"market": "sweden", "channel": "disney channel", "id": "29"},
    {"market": "sweden", "channel": "tv4 film", "id": "29"},
    {"market": "sweden", "channel": "tv6 se", "id": "29"},
    {"market": "sweden", "channel": "tv4 fakta", "id": "29"},
    {"market": "sweden", "channel": "tv4 guld", "id": "29"},
    {"market": "sweden", "channel": "eurosport se", "id": "29"},
    {"market": "sweden", "channel": "national geographic", "id": "29"},
    {"market": "sweden", "channel": "svt 24", "id": "29"},
    {"market": "sweden", "channel": "history", "id": "29"},
    {"market": "sweden", "channel": "tv12 se", "id": "29"},
    {"market": "sweden", "channel": "tv10 se", "id": "29"},
    {"market": "sweden", "channel": "tlc", "id": "29"},
    {"market": "sweden", "channel": "investigation discovery", "id": "29"},
    {"market": "sweden", "channel": "kanal 11", "id": "29"},
    {"market": "sweden", "channel": "eurosport 2 se", "id": "29"},
    {"market": "sweden", "channel": "tv4 sportkanalen se", "id": "29"},
    {"market": "sweden", "channel": "godare", "id": "29"},
    {"market": "sweden", "channel": "svt 2", "id": "29"},
    {"market": "sweden", "channel": "svtb", "id": "29"},
    {"market": "sweden", "channel": "tv8 se", "id": "29"},
    {"market": "sweden", "channel": "kunskapskanalen", "id": "29"},
    # --- Switzerland ---
    {"market": "switzerland", "channel": "srf info", "id": "6"},
    {"market": "switzerland", "channel": "rts un", "id": "6"},
    {"market": "switzerland", "channel": "3 sat ch", "id": "6"},
    {"market": "switzerland", "channel": "m6 ch", "id": "6"},
    {"market": "switzerland", "channel": "nickelodeon ch", "id": "6"},
    {"market": "switzerland", "channel": "rtl ch", "id": "6"},
    {"market": "switzerland", "channel": "tv24", "id": "6"},
    {"market": "switzerland", "channel": "zdf ch", "id": "6"},
    {"market": "switzerland", "channel": "orf 2", "id": "6"},
    {"market": "switzerland", "channel": "orf 1", "id": "6"},
    {"market": "switzerland", "channel": "france 2 ch", "id": "6"},
    {"market": "switzerland", "channel": "france 3 ch", "id": "6"},
    {"market": "switzerland", "channel": "rai 1", "id": "6"},
    {"market": "switzerland", "channel": "rai 2", "id": "6"},
    {"market": "switzerland", "channel": "canale 5 ch", "id": "6"},
    {"market": "switzerland", "channel": "italia 1 ch", "id": "6"},
    {"market": "switzerland", "channel": "blue zoom d", "id": "6"},
    {"market": "switzerland", "channel": "teleticino", "id": "6"},
    {"market": "switzerland", "channel": "swiss1", "id": "6"},
    {"market": "switzerland", "channel": "tele 1 ch", "id": "6"},
    {"market": "switzerland", "channel": "tele m1 ch", "id": "6"},
    {"market": "switzerland", "channel": "tele baern", "id": "6"},
    {"market": "switzerland", "channel": "tele zueri", "id": "6"},
    {"market": "switzerland", "channel": "tvo ch", "id": "6"},
    {"market": "switzerland", "channel": "srf 1", "id": "6"},
    {"market": "switzerland", "channel": "srf 2", "id": "6"},
    {"market": "switzerland", "channel": "rsi la 1", "id": "6"},
    {"market": "switzerland", "channel": "rsi la 2", "id": "6"},
    {"market": "switzerland", "channel": "rts deux", "id": "6"},
    {"market": "switzerland", "channel": "kabel 1 ch", "id": "6"},
    {"market": "switzerland", "channel": "pro7 ch", "id": "6"},
    {"market": "switzerland", "channel": "pro7 maxx ch", "id": "6"},
    {"market": "switzerland", "channel": "rtl 2 ch", "id": "6"},
    {"market": "switzerland", "channel": "sat.1 ch", "id": "6"},
    {"market": "switzerland", "channel": "vox ch", "id": "6"},
    {"market": "switzerland", "channel": "super rtl ch", "id": "6"},
    {"market": "switzerland", "channel": "ard ch", "id": "6"},
    {"market": "switzerland", "channel": "3+", "id": "6"},
    {"market": "switzerland", "channel": "tf1 ch", "id": "6"},
    {"market": "switzerland", "channel": "mysports eins", "id": "6"},
    {"market": "switzerland", "channel": "mysports un", "id": "6"},
    {"market": "switzerland", "channel": "tv25", "id": "6"},
    {"market": "switzerland", "channel": "nitro ch", "id": "6"},
    {"market": "switzerland", "channel": "s1", "id": "6"},
    {"market": "switzerland", "channel": "5+", "id": "6"},
    {"market": "switzerland", "channel": "6+", "id": "6"},
    {"market": "switzerland", "channel": "puls 8", "id": "6"},
    {"market": "switzerland", "channel": "sixx", "id": "6"},
    {"market": "switzerland", "channel": "tvo - das ostschweizer fernsehen", "id": "6"},
    {"market": "switzerland", "channel": "4+", "id": "6"},
    # --- Taiwan ---
    {"market": "taiwan", "channel": "ftv news", "id": "87"},
    {"market": "taiwan", "channel": "ctv news channel", "id": "87"},
    {"market": "taiwan", "channel": "setn", "id": "87"},
    {"market": "taiwan", "channel": "ftv", "id": "87"},
    {"market": "taiwan", "channel": "dazn 1 tw", "id": "87"},
    {"market": "taiwan", "channel": "tvbs taiwan", "id": "87"},
    {"market": "taiwan", "channel": "tvbs news", "id": "87"},
    {"market": "taiwan", "channel": "et-n eastern news", "id": "87"},
    {"market": "taiwan", "channel": "z channel", "id": "87"},
    {"market": "taiwan", "channel": "ntvn", "id": "87"},
    {"market": "taiwan", "channel": "set-f", "id": "87"},
    {"market": "taiwan", "channel": "ttv-g", "id": "87"},
    {"market": "taiwan", "channel": "cts news channel", "id": "87"},
    {"market": "taiwan", "channel": "ttv-n", "id": "87"},
    {"market": "taiwan", "channel": "momok", "id": "87"},
    {"market": "taiwan", "channel": "dazn 2 tw", "id": "87"},
    {"market": "taiwan", "channel": "efnc", "id": "87"},
    {"market": "taiwan", "channel": "era news", "id": "87"},
    {"market": "taiwan", "channel": "vlspt", "id": "87"},
    {"market": "taiwan", "channel": "stv", "id": "87"},
    {"market": "taiwan", "channel": "ettv", "id": "87"},
    {"market": "taiwan", "channel": "ttv-f", "id": "87"},
    {"market": "taiwan", "channel": "much tv", "id": "87"},
    {"market": "taiwan", "channel": "ubn", "id": "87"},
    {"market": "taiwan", "channel": "et-d", "id": "87"},
    {"market": "taiwan", "channel": "ptv", "id": "87"},
    {"market": "taiwan", "channel": "ftv travel", "id": "87"},
    {"market": "taiwan", "channel": "cts", "id": "87"},
    {"market": "taiwan", "channel": "ustv", "id": "87"},
    {"market": "taiwan", "channel": "jet", "id": "87"},
    {"market": "taiwan", "channel": "da ai tv", "id": "87"},
    {"market": "taiwan", "channel": "vlmax", "id": "87"},
    {"market": "taiwan", "channel": "ftv one", "id": "87"},
    {"market": "taiwan", "channel": "ctv classic", "id": "87"},
    {"market": "taiwan", "channel": "ttv", "id": "87"},
    {"market": "taiwan", "channel": "ctv main channel", "id": "87"},
    {"market": "taiwan", "channel": "ctv-b", "id": "87"},
    {"market": "taiwan", "channel": "ontv", "id": "87"},
    {"market": "taiwan", "channel": "sanli news", "id": "87"},
    {"market": "taiwan", "channel": "gtv-1", "id": "87"},
    {"market": "taiwan", "channel": "sl2", "id": "87"},
    {"market": "taiwan", "channel": "asia", "id": "87"},
    {"market": "taiwan", "channel": "elta sports 1", "id": "87"},
    {"market": "taiwan", "channel": "elta sports 2", "id": "87"},
    {"market": "taiwan", "channel": "elta sports 3", "id": "87"},
    {"market": "taiwan", "channel": "elta sports 4", "id": "87"},
    {"market": "taiwan", "channel": "yoyo", "id": "87"},
    # --- Thailand ---
    {"market": "thailand", "channel": "pptv", "id": "43"},
    {"market": "thailand", "channel": "nation tv", "id": "43"},
    {"market": "thailand", "channel": "tnn24", "id": "43"},
    {"market": "thailand", "channel": "true4u", "id": "43"},
    {"market": "thailand", "channel": "workpoint tv", "id": "43"},
    {"market": "thailand", "channel": "mcot hd", "id": "43"},
    {"market": "thailand", "channel": "thairath tv", "id": "43"},
    {"market": "thailand", "channel": "channel 3 th", "id": "43"},
    {"market": "thailand", "channel": "mono 29", "id": "43"},
    {"market": "thailand", "channel": "one", "id": "43"},
    {"market": "thailand", "channel": "t sports channel", "id": "43"},
    {"market": "thailand", "channel": "channel 7 th", "id": "43"},
    {"market": "thailand", "channel": "nbt", "id": "43"},
    {"market": "thailand", "channel": "amarin tv", "id": "43"},
    {"market": "thailand", "channel": "channel 8 th", "id": "43"},
    {"market": "thailand", "channel": "gmm25", "id": "43"},
    # --- Turkey ---
    {"market": "turkey", "channel": "360 tv", "id": "33"},
    {"market": "turkey", "channel": "a haber", "id": "33"},
    {"market": "turkey", "channel": "a spor", "id": "33"},
    {"market": "turkey", "channel": "atv turkey", "id": "33"},
    {"market": "turkey", "channel": "beyaz tv", "id": "33"},
    {"market": "turkey", "channel": "cnn turk", "id": "33"},
    {"market": "turkey", "channel": "now turkey", "id": "33"},
    {"market": "turkey", "channel": "habertuerk tv", "id": "33"},
    {"market": "turkey", "channel": "halk tv", "id": "33"},
    {"market": "turkey", "channel": "kanal 7 int.", "id": "33"},
    {"market": "turkey", "channel": "kanal d", "id": "33"},
    {"market": "turkey", "channel": "krt tv", "id": "33"},
    {"market": "turkey", "channel": "ntv turkey", "id": "33"},
    {"market": "turkey", "channel": "show tv", "id": "33"},
    {"market": "turkey", "channel": "star tv", "id": "33"},
    {"market": "turkey", "channel": "tgrt haber", "id": "33"},
    {"market": "turkey", "channel": "trt 1", "id": "33"},
    {"market": "turkey", "channel": "trt kurdi", "id": "33"},
    {"market": "turkey", "channel": "trt haber", "id": "33"},
    {"market": "turkey", "channel": "trt spor", "id": "33"},
    {"market": "turkey", "channel": "tv8.5", "id": "33"},
    {"market": "turkey", "channel": "ulke tv", "id": "33"},
    {"market": "turkey", "channel": "ulusal kanal", "id": "33"},
    {"market": "turkey", "channel": "tele1", "id": "33"},
    {"market": "turkey", "channel": "tv100", "id": "33"},
    {"market": "turkey", "channel": "haber global", "id": "33"},
    {"market": "turkey", "channel": "trt spor yildiz", "id": "33"},
    {"market": "turkey", "channel": "bengu turk", "id": "33"},
    {"market": "turkey", "channel": "flash haber tv", "id": "33"},
    {"market": "turkey", "channel": "sozcu tv", "id": "33"},
    {"market": "turkey", "channel": "dmax turkey", "id": "33"},
    # --- Usa ---
    {"market": "usa", "channel": "american heroes channel", "id": "47"},
    {"market": "usa", "channel": "animal planet", "id": "47"},
    {"market": "usa", "channel": "discovery en espanol", "id": "47"},
    {"market": "usa", "channel": "fyi", "id": "47"},
    {"market": "usa", "channel": "hln", "id": "47"},
    {"market": "usa", "channel": "investigation discovery", "id": "47"},
    {"market": "usa", "channel": "discovery turbo", "id": "47"},
    {"market": "usa", "channel": "nat geo wild", "id": "47"},
    {"market": "usa", "channel": "national geographic", "id": "47"},
    {"market": "usa", "channel": "own", "id": "47"},
    {"market": "usa", "channel": "oxygen", "id": "47"},
    {"market": "usa", "channel": "science", "id": "47"},
    {"market": "usa", "channel": "tlc", "id": "47"},
    {"market": "usa", "channel": "tv one", "id": "47"},
    {"market": "usa", "channel": "vice tv", "id": "47"},
    {"market": "usa", "channel": "national geographic mundo", "id": "47"},
    {"market": "usa", "channel": "smithsonian channel", "id": "47"},
    {"market": "usa", "channel": "story television", "id": "47"},
    {"market": "usa", "channel": "discovery life channel", "id": "47"},
    {"market": "usa", "channel": "the weather channel", "id": "47"},
    {"market": "usa", "channel": "fox news", "id": "47"},
    {"market": "usa", "channel": "newsnation", "id": "47"},
    {"market": "usa", "channel": "newsmax tv", "id": "47"},
    {"market": "usa", "channel": "court tv", "id": "47"},
    {"market": "usa", "channel": "msnbc", "id": "47"},
    {"market": "usa", "channel": "cnn espanol", "id": "47"},
    {"market": "usa", "channel": "comedy.tv", "id": "47"},
    {"market": "usa", "channel": "bein sports usa", "id": "47"},
    {"market": "usa", "channel": "fox sports 1 usa", "id": "47"},
    {"market": "usa", "channel": "espnu", "id": "47"},
    {"market": "usa", "channel": "fox sports 2 usa", "id": "47"},
    {"market": "usa", "channel": "gsn", "id": "47"},
    {"market": "usa", "channel": "e", "id": "47"},
    {"market": "usa", "channel": "great american family", "id": "47"},
    {"market": "usa", "channel": "hallmark mystery", "id": "47"},
    {"market": "usa", "channel": "mtv", "id": "47"},
    {"market": "usa", "channel": "mtv2", "id": "47"},
    {"market": "usa", "channel": "ovation", "id": "47"},
    {"market": "usa", "channel": "sundance tv", "id": "47"},
    {"market": "usa", "channel": "tbs usa", "id": "47"},
    {"market": "usa", "channel": "adult swim", "id": "47"},
    {"market": "usa", "channel": "comedy central", "id": "47"},
    {"market": "usa", "channel": "fxx", "id": "47"},
    {"market": "usa", "channel": "metv toons", "id": "47"},
    {"market": "usa", "channel": "antenna tv", "id": "47"},
    {"market": "usa", "channel": "black entertainment tv", "id": "47"},
    {"market": "usa", "channel": "catchy comedy", "id": "47"},
    {"market": "usa", "channel": "cleo tv", "id": "47"},
    {"market": "usa", "channel": "cozitv", "id": "47"},
    {"market": "usa", "channel": "dabl", "id": "47"},
    {"market": "usa", "channel": "galavision", "id": "47"},
    {"market": "usa", "channel": "ifc", "id": "47"},
    {"market": "usa", "channel": "me tv", "id": "47"},
    {"market": "usa", "channel": "nick-at-nite", "id": "47"},
    {"market": "usa", "channel": "thegrio tv", "id": "47"},
    {"market": "usa", "channel": "tv land", "id": "47"},
    {"market": "usa", "channel": "baby first tv", "id": "47"},
    {"market": "usa", "channel": "boomerang", "id": "47"},
    {"market": "usa", "channel": "disney channel", "id": "47"},
    {"market": "usa", "channel": "disney xd", "id": "47"},
    {"market": "usa", "channel": "nick jr.", "id": "47"},
    {"market": "usa", "channel": "charge", "id": "47"},
    {"market": "usa", "channel": "comet tv", "id": "47"},
    {"market": "usa", "channel": "hallmark family", "id": "47"},
    {"market": "usa", "channel": "ion television", "id": "47"},
    {"market": "usa", "channel": "ion mystery", "id": "47"},
    {"market": "usa", "channel": "ion plus", "id": "47"},
    {"market": "usa", "channel": "pop tv", "id": "47"},
    {"market": "usa", "channel": "reelz", "id": "47"},
    {"market": "usa", "channel": "start tv", "id": "47"},
    {"market": "usa", "channel": "up", "id": "47"},
    {"market": "usa", "channel": "usa network", "id": "47"},
    {"market": "usa", "channel": "wetv", "id": "47"},
    {"market": "usa", "channel": "discovery channel usa", "id": "47"},
    {"market": "usa", "channel": "justice central", "id": "47"},
    {"market": "usa", "channel": "espn 2 usa", "id": "47"},
    {"market": "usa", "channel": "nba tv", "id": "47"},
    {"market": "usa", "channel": "btn", "id": "47"},
    {"market": "usa", "channel": "tudn usa", "id": "47"},
    {"market": "usa", "channel": "telemundo", "id": "47"},
    {"market": "usa", "channel": "espn deportes", "id": "47"},
    {"market": "usa", "channel": "fox deportes", "id": "47"},
    {"market": "usa", "channel": "univision", "id": "47"},
    {"market": "usa", "channel": "cnn usa", "id": "47"},
    {"market": "usa", "channel": "cnbc usa", "id": "47"},
    {"market": "usa", "channel": "cooking channel", "id": "47"},
    {"market": "usa", "channel": "food network star", "id": "47"},
    {"market": "usa", "channel": "discovery familia", "id": "47"},
    {"market": "usa", "channel": "discovery family", "id": "47"},
    {"market": "usa", "channel": "hgtv usa", "id": "47"},
    {"market": "usa", "channel": "diy network", "id": "47"},
    {"market": "usa", "channel": "destination america", "id": "47"},
    {"market": "usa", "channel": "hogar de hgtv", "id": "47"},
    {"market": "usa", "channel": "rfd tv", "id": "47"},
    {"market": "usa", "channel": "travel channel", "id": "47"},
    {"market": "usa", "channel": "estrella tv", "id": "47"},
    {"market": "usa", "channel": "logo", "id": "47"},
    {"market": "usa", "channel": "gettv", "id": "47"},
    {"market": "usa", "channel": "tbd", "id": "47"},
    {"market": "usa", "channel": "heroes + icons", "id": "47"},
    {"market": "usa", "channel": "insp", "id": "47"},
    {"market": "usa", "channel": "hallmark channel", "id": "47"},
    {"market": "usa", "channel": "lifetime movie network", "id": "47"},
    {"market": "usa", "channel": "lifetime", "id": "47"},
    {"market": "usa", "channel": "starz primary", "id": "47"},
    {"market": "usa", "channel": "a+e network", "id": "47"},
    {"market": "usa", "channel": "history", "id": "47"},
    {"market": "usa", "channel": "disney junior", "id": "47"},
    {"market": "usa", "channel": "family ent tv", "id": "47"},
    {"market": "usa", "channel": "nicktoons", "id": "47"},
    {"market": "usa", "channel": "telexitos", "id": "47"},
    {"market": "usa", "channel": "turner network television", "id": "47"},
    {"market": "usa", "channel": "teennick", "id": "47"},
    {"market": "usa", "channel": "nbc universo", "id": "47"},
    {"market": "usa", "channel": "the cowboy channel", "id": "47"},
    {"market": "usa", "channel": "the golf channel usa", "id": "47"},
    {"market": "usa", "channel": "tennis channel", "id": "47"},
    {"market": "usa", "channel": "bounce tv", "id": "47"},
    {"market": "usa", "channel": "grit", "id": "47"},
    {"market": "usa", "channel": "fx movie channel", "id": "47"},
    {"market": "usa", "channel": "trutv", "id": "47"},
    {"market": "usa", "channel": "showtime prime", "id": "47"},
    {"market": "usa", "channel": "bet her", "id": "47"},
    {"market": "usa", "channel": "bravo", "id": "47"},
    {"market": "usa", "channel": "nfl network", "id": "47"},
    {"market": "usa", "channel": "paramount network", "id": "47"},
    {"market": "usa", "channel": "bein sports espanol usa", "id": "47"},
    {"market": "usa", "channel": "vh1", "id": "47"},
    {"market": "usa", "channel": "laff", "id": "47"},
    {"market": "usa", "channel": "syfy", "id": "47"},
    {"market": "usa", "channel": "unimas", "id": "47"},
    {"market": "usa", "channel": "bbc america", "id": "47"},
    {"market": "usa", "channel": "nbc true crmz", "id": "47"},
    {"market": "usa", "channel": "espn usa", "id": "47"},
    {"market": "usa", "channel": "amc", "id": "47"},
    {"market": "usa", "channel": "fx", "id": "47"},
    {"market": "usa", "channel": "mlb network", "id": "47"},
    {"market": "usa", "channel": "cmt", "id": "47"},
    {"market": "usa", "channel": "hbo prime", "id": "47"},
    {"market": "usa", "channel": "cbs", "id": "47"},
    {"market": "usa", "channel": "nbc", "id": "47"},
    {"market": "usa", "channel": "abc", "id": "47"},
    {"market": "usa", "channel": "fox business network", "id": "47"},
    {"market": "usa", "channel": "tlnovelas", "id": "47"},
    {"market": "usa", "channel": "freeform", "id": "47"},
    {"market": "usa", "channel": "cartoon network", "id": "47"},
    {"market": "usa", "channel": "nickelodeon", "id": "47"},
    {"market": "usa", "channel": "cw", "id": "47"},
    {"market": "usa", "channel": "fox usa", "id": "47"},
    {"market": "usa", "channel": "motortrend", "id": "47"},
    {"market": "usa", "channel": "galanovelas", "id": "47"},
    # --- Ukraine ---
    {"market": "ukraine", "channel": "ntn", "id": "34"},
    {"market": "ukraine", "channel": "xsport", "id": "34"},
    {"market": "ukraine", "channel": "we-ukraine+", "id": "34"},
    {"market": "ukraine", "channel": "suspilne sport", "id": "34"},
    {"market": "ukraine", "channel": "2+2", "id": "34"},
    {"market": "ukraine", "channel": "enter film", "id": "34"},
    {"market": "ukraine", "channel": "oce", "id": "34"},
    {"market": "ukraine", "channel": "unian", "id": "34"},
    {"market": "ukraine", "channel": "suspilne kultura", "id": "34"},
    {"market": "ukraine", "channel": "1+1", "id": "34"},
    {"market": "ukraine", "channel": "ictv2", "id": "34"},
    {"market": "ukraine", "channel": "zoom", "id": "34"},
    # --- United Kingdom ---
    {"market": "united kingdom", "channel": "channel 5", "id": "35"},
    {"market": "united kingdom", "channel": "bbc1", "id": "35"},
    {"market": "united kingdom", "channel": "bbc2", "id": "35"},
    {"market": "united kingdom", "channel": "bbc3", "id": "35"},
    {"market": "united kingdom", "channel": "bbc4", "id": "35"},
    {"market": "united kingdom", "channel": "bbc news", "id": "35"},
    {"market": "united kingdom", "channel": "channel 4", "id": "35"},
    {"market": "united kingdom", "channel": "itv quiz", "id": "35"},
    {"market": "united kingdom", "channel": "itv 1", "id": "35"},
    {"market": "united kingdom", "channel": "itv 2", "id": "35"},
    {"market": "united kingdom", "channel": "itv 3", "id": "35"},
    {"market": "united kingdom", "channel": "itv 4", "id": "35"},
    {"market": "united kingdom", "channel": "premier sports 1 uk", "id": "35"},
    {"market": "united kingdom", "channel": "premier sports 2 uk", "id": "35"},
    {"market": "united kingdom", "channel": "quest", "id": "35"},
    {"market": "united kingdom", "channel": "s4c", "id": "35"},
    {"market": "united kingdom", "channel": "sky mix", "id": "35"},
    {"market": "united kingdom", "channel": "sky news uk", "id": "35"},
    {"market": "united kingdom", "channel": "sky showcase uk", "id": "35"},
    {"market": "united kingdom", "channel": "sky showcase +1", "id": "35"},
    {"market": "united kingdom", "channel": "sky sports cricket", "id": "35"},
    {"market": "united kingdom", "channel": "sky sports f1 uk", "id": "35"},
    {"market": "united kingdom", "channel": "sky sports football", "id": "35"},
    {"market": "united kingdom", "channel": "sky sports golf uk", "id": "35"},
    {"market": "united kingdom", "channel": "sky sports main event", "id": "35"},
    {"market": "united kingdom", "channel": "sky sports mix uk", "id": "35"},
    {"market": "united kingdom", "channel": "sky sports news uk", "id": "35"},
    {"market": "united kingdom", "channel": "sky sports premier league uk", "id": "35"},
    {"market": "united kingdom", "channel": "sky sports racing", "id": "35"},
    {"market": "united kingdom", "channel": "sky sports tennis uk", "id": "35"},
    {"market": "united kingdom", "channel": "sky sports+ uk", "id": "35"},
    {"market": "united kingdom", "channel": "tnt sports 1", "id": "35"},
    {"market": "united kingdom", "channel": "tnt sports 2", "id": "35"},
    {"market": "united kingdom", "channel": "tnt sports 3", "id": "35"},
    {"market": "united kingdom", "channel": "tnt sports 4", "id": "35"},
    {"market": "united kingdom", "channel": "u+dave", "id": "35"},
    {"market": "united kingdom", "channel": "sky sports action", "id": "35"},
    # --- Vietnam ---
    {"market": "vietnam", "channel": "vtv3", "id": "68"},
    {"market": "vietnam", "channel": "vtv1", "id": "68"},
    {"market": "vietnam", "channel": "htv 7", "id": "68"},
    {"market": "vietnam", "channel": "antv", "id": "68"},
    {"market": "vietnam", "channel": "vtv9", "id": "68"},
    {"market": "vietnam", "channel": "htv 9", "id": "68"},
    {"market": "vietnam", "channel": "atv2 (bao va ptth an giang)", "id": "68"},
    {"market": "vietnam", "channel": "ltv2 (bao va ptth lam dong)", "id": "68"},
    {"market": "vietnam", "channel": "btv (bao va ptth bac ninh)", "id": "68"},
    {"market": "vietnam", "channel": "ctv (bao va ptth ca mau)", "id": "68"},
    {"market": "vietnam", "channel": "dn1nrtv (bao va ptth dong nai)", "id": "68"},
    {"market": "vietnam", "channel": "dnrt1 (bao va ptth da nang)", "id": "68"},
    {"market": "vietnam", "channel": "hanoi tv 1", "id": "68"},
    {"market": "vietnam", "channel": "hanoi tv 2", "id": "68"},
    {"market": "vietnam", "channel": "bht tv (th bao ha tinh)", "id": "68"},
    {"market": "vietnam", "channel": "htv2 - vie channel", "id": "68"},
    {"market": "vietnam", "channel": "htv3", "id": "68"},
    {"market": "vietnam", "channel": "hy (bao va ptth hung yen)", "id": "68"},
    {"market": "vietnam", "channel": "atv1 (bao va ptth an giang)", "id": "68"},
    {"market": "vietnam", "channel": "ktv (bao va ptth khanh hoa)", "id": "68"},
    {"market": "vietnam", "channel": "ltv1 (bao va ptth lam dong)", "id": "68"},
    {"market": "vietnam", "channel": "ntv (bao va ptth nghe an)", "id": "68"},
    {"market": "vietnam", "channel": "ktv1 (bao va ptth khanh hoa)", "id": "68"},
    {"market": "vietnam", "channel": "qtv (bao va ptth quang ninh)", "id": "68"},
    {"market": "vietnam", "channel": "sctv 11", "id": "68"},
    {"market": "vietnam", "channel": "sctv 4", "id": "68"},
    {"market": "vietnam", "channel": "thp3 (bao va ptth hai phong)", "id": "68"},
    {"market": "vietnam", "channel": "thdt1 (bao va ptth dong thap)", "id": "68"},
    {"market": "vietnam", "channel": "thp (bao va ptth hai phong)", "id": "68"},
    {"market": "vietnam", "channel": "cantho1 (bao va ptth can tho)", "id": "68"},
    {"market": "vietnam", "channel": "thvl1 (bao va ptth vinh long)", "id": "68"},
    {"market": "vietnam", "channel": "thvl2 (bao va ptth vinh long)", "id": "68"},
    {"market": "vietnam", "channel": "huetv (bao va ptth hue)", "id": "68"},
    {"market": "vietnam", "channel": "ttv (bao va ptth thanh hoa)", "id": "68"},
    {"market": "vietnam", "channel": "ttv2 (bao va ptth tay ninh)", "id": "68"},
    {"market": "vietnam", "channel": "vtv2", "id": "68"},
    {"market": "vietnam", "channel": "vtv5 tay nam bo", "id": "68"},
    {"market": "vietnam", "channel": "vtv8", "id": "68"},
    {"market": "vietnam", "channel": "vtvcab on sports+", "id": "68"},
    {"market": "vietnam", "channel": "thvl3 (bao va ptth vinh long)", "id": "68"},
    {"market": "vietnam", "channel": "vtv can tho", "id": "68"},
    {"market": "vietnam", "channel": "htv the thao", "id": "68"},
    {"market": "vietnam", "channel": "on football", "id": "68"},
    {"market": "vietnam", "channel": "vtvcab on sports", "id": "68"},
    {"market": "vietnam", "channel": "ttv1 (bao va ptth tay ninh)", "id": "68"},
]

# --- HELPER FUNCTIONS (MATCHING STREAMLIT LOGIC) ---

def parse_custom_date(date_str):
    """Parses mixed date formats found in BSA headers."""
    if isinstance(date_str, datetime): return date_str
    s = str(date_str).strip()
    # Remove ordinal suffixes like 1st, 2nd, 3rd, 4th
    s_clean = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', s, flags=re.IGNORECASE)
    for fmt in ('%d %b %Y', '%Y-%m-%d', '%d-%m-%Y', '%Y-%m-%d %H:%M:%S', '%m/%d/%Y', '%Y/%m/%d'):
        try: return datetime.strptime(s_clean, fmt)
        except ValueError: continue
    return None

def extract_monitoring_period(df_info):
    """Extracts date range from Rosco 'Info' sheet."""
    monitor_row = df_info[df_info.iloc[:, 0].astype(str).str.contains("Monitoring Periods", na=False)]
    if not monitor_row.empty:
        dates = re.findall(r'\d{4}-\d{2}-\d{2}', str(monitor_row.iloc[0, 1]))
        if len(dates) >= 2:
            return datetime.strptime(dates[0], '%Y-%m-%d'), datetime.strptime(dates[1], '%Y-%m-%d')
    return None, None

def _clean_name_strict(name):
    """Keeps brackets/codes. Used for BSA & Mandatory checks."""
    if pd.isna(name): return ""
    s = str(name).strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s

def _clean_name_lenient(name):
    """Removes brackets and codes. Used for Rosco matching."""
    if pd.isna(name): return ""
    s = str(name)
    s = re.sub(r"\(.*?\)|\[.*?\]", "", s) # Remove content inside () or []
    s = re.split(r"[-–—]", s)[0]          # Split at dashes
    s = re.sub(r"[^0-9a-zA-Z\s]", " ", s) # Remove special chars
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s

def _clean_market(m): 
    if pd.isna(m): return ""
    return str(m).strip().lower()

def _clean_id(val): 
    if pd.isna(val): return ""
    s = str(val).strip()
    return s[:-2] if s.endswith(".0") else s

# --- API ENDPOINT ---
@qc_router.post("/early-warning")
async def generate_early_warning(
    bsa_file: UploadFile = File(...),
    rosco_file: Optional[UploadFile] = File(None)
):
    try:
        # 1. READ BSA FILE
        bsa_content = await bsa_file.read()
        df_bsa = pd.read_excel(io.BytesIO(bsa_content))
        
        # Identify Columns
        cols_lower = {str(c).lower(): c for c in df_bsa.columns}
        bsa_chan_c = next((cols_lower[c] for c in cols_lower if "channel" in c and "id" not in c), None)
        bsa_mkt_c = next((cols_lower[c] for c in cols_lower if "market" in c), None)
        bsa_id_c = next((cols_lower[c] for c in cols_lower if "channel" in c and "id" in c), None)
        
        if not bsa_chan_c or not bsa_mkt_c:
            raise HTTPException(status_code=400, detail="Could not identify 'Channel' or 'Market' columns in BSA file.")

        # Deduplicate
        df_bsa.drop_duplicates(subset=[bsa_mkt_c, bsa_chan_c], inplace=True)
        
        # Identify Date Columns
        metadata_cols = {bsa_chan_c, bsa_mkt_c, bsa_id_c} if bsa_id_c else {bsa_chan_c, bsa_mkt_c}
        date_cols = [c for c in df_bsa.columns if c not in metadata_cols and parse_custom_date(c) is not None]
        
        # Sort date columns chronologically
        date_cols.sort(key=lambda x: parse_custom_date(x))

        # --- LOGIC 1: BSA CONSOLIDATED VIEW ---
        bsa_view = []
        mandatory_set = set(_clean_name_strict(x) for x in MANDATORY_CHANNELS)
        trend_stats_map = {str(d): {"Scheduled": 0, "Processing Gaps": 0, "No Schedule": 0} for d in date_cols}

        # Pre-build BSA Lookups for Rosco Logic later
        bsa_region_lookup = {}
        bsa_id_lookup = {}

        for _, row in df_bsa.iterrows():
            cn = str(row[bsa_chan_c])
            mkt = str(row[bsa_mkt_c])
            cid = str(row[bsa_id_c]) if bsa_id_c else ""
            
            # Store for Rosco (Lenient Matching)
            lenient_key = (_clean_market(mkt), _clean_name_lenient(cn))
            bsa_region_lookup[lenient_key] = row.to_dict()
            if bsa_id_c and pd.notna(row[bsa_id_c]):
                bsa_id_lookup[_clean_id(row[bsa_id_c])] = row.to_dict()

            # Critical Check (Strict)
            is_crit = "CRITICAL" if _clean_name_strict(cn) in mandatory_set else "Non-Critical"
            
            # Status Logic
            row_statuses = [str(row[d]).lower() for d in date_cols]
            
            if any("processing gaps" in s for s in row_statuses): 
                final_s = "FLAG: Processing Gaps"
            elif all("no schedule" in s for s in row_statuses) and row_statuses: 
                final_s = "FLAG: No Schedule"
            elif any("no schedule" in s for s in row_statuses): 
                final_s = "FLAG: Partial Schedule"
            else: 
                final_s = "OK"

            # Update Trend Stats
            for d in date_cols:
                val = str(row[d]).lower()
                d_key = str(d)
                if "processing gaps" in val: trend_stats_map[d_key]["Processing Gaps"] += 1
                elif "no schedule" in val: trend_stats_map[d_key]["No Schedule"] += 1
                elif "scheduled" in val or "ok" in val: trend_stats_map[d_key]["Scheduled"] += 1

            record = {
                "TV Channel": cn,
                "Market": mkt,
                "Critical Channel": is_crit,
                "Final Status": final_s,
                **{str(d): row[d] for d in date_cols} # Flatten dates
            }
            bsa_view.append(record)

        # --- LOGIC 2: MANDATORY AUDIT ---
        bsa_lookup_strict = set(df_bsa[bsa_chan_c].astype(str).apply(_clean_name_strict))
        mandatory_audit = []
        for m_chan in MANDATORY_CHANNELS:
            found = _clean_name_strict(m_chan) in bsa_lookup_strict
            mandatory_audit.append({
                "Channel": m_chan,
                "Found": "YES" if found else "NO",
                "Status": "OK" if found else "MISSING"
            })

        # --- LOGIC 3: ROSCO COMPARISON (Implemented from Streamlit Logic) ---
        rosco_view = []
        if rosco_file:
            rosco_content = await rosco_file.read()
            xls_rosco = pd.ExcelFile(io.BytesIO(rosco_content))
            
            # 1. Extract Dates from "Info" sheet
            start_scope, end_scope = None, None
            info_sheet = next((s for s in xls_rosco.sheet_names if "Info" in s), None)
            if info_sheet:
                df_info = pd.read_excel(xls_rosco, sheet_name=info_sheet)
                start_scope, end_scope = extract_monitoring_period(df_info)
            
            # 2. Determine Matching Dates
            matching_dates = date_cols
            if start_scope and end_scope:
                matching_dates = [c for c in date_cols if start_scope <= parse_custom_date(c) <= end_scope]

            # 3. Process "Monitoring" Sheet
            sheet_name = next((s for s in xls_rosco.sheet_names if "Monitoring" in s), None)
            if sheet_name:
                df_rosco = pd.read_excel(xls_rosco, sheet_name=sheet_name)
                
                # Create Aura Lookup Map
                aura_map = {(_clean_market(r['market']), _clean_name_lenient(r['channel'])): r['id'] for r in AURA_MASTER_DATA}
                
                for _, row in df_rosco.iterrows():
                    cn = str(row.get('ChannelName', ''))
                    mkt = str(row.get('ChannelCountry', ''))
                    
                    cl_lenient = _clean_name_lenient(cn)
                    ml_clean = _clean_market(mkt)
                    
                    # Logic: Check Aura
                    aura_id = aura_map.get((ml_clean, cl_lenient))
                    in_aura = (ml_clean, cl_lenient) in aura_map
                    
                    # Logic: Check BSA (ID first, then Name)
                    fnd, brow = False, None
                    if aura_id and aura_id in bsa_id_lookup:
                        fnd, brow = True, bsa_id_lookup[aura_id]
                    elif (ml_clean, cl_lenient) in bsa_region_lookup:
                        fnd, brow = True, bsa_region_lookup[(ml_clean, cl_lenient)]
                    
                    # Logic: Determine Status
                    if not fnd: 
                        final_s = "CRITICAL: Missing in Both" if not in_aura else "FLAG: Not in BSA"
                    else:
                        statuses = [str(brow.get(d, "Not in BSA")).lower() for d in matching_dates]
                        
                        if not statuses: 
                            final_s = "OK (No dates)"
                        elif statuses.count("no schedule") == len(statuses): 
                            final_s = "FLAG: Found (No Schedules)"
                        elif any("processing gaps" in s for s in statuses): 
                            final_s = "FLAG: Processing Gaps"
                        elif not in_aura: 
                            final_s = "CRITICAL: Not in Aura"
                        else: 
                            final_s = "OK"

                    r_entry = {
                        "Channel": cn,
                        "Market": mkt,
                        "IN AURA": "YES" if in_aura else "NO",
                        "IN BSA": "YES" if fnd else "NO",
                        "Final Status": final_s
                    }
                    
                    # Add date columns overlap if found
                    if fnd and brow:
                        for d in matching_dates:
                            r_entry[str(d)] = str(brow.get(d, "N/A"))
                            
                    rosco_view.append(r_entry)

        return JSONResponse({
            "bsa_view": bsa_view,
            "trend_stats": [{"Date": str(k), **v} for k, v in trend_stats_map.items()],
            "mandatory_audit": mandatory_audit,
            "rosco_view": rosco_view,
            "date_columns": [str(d) for d in date_cols]
        })

    except Exception as e:
        logger.error(f"Error in early warning dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


HARDCODED_SCHEDULE = [
    {"Session": "Practice 1", "Date": "4-Jul-2025", "Start Time": "11:30:00", "End Time": "12:30:00"},
    {"Session": "Practice 2", "Date": "4-Jul-2025", "Start Time": "15:00:00", "End Time": "16:00:00"},
    {"Session": "Practice 3", "Date": "5-Jul-2025", "Start Time": "10:30:00", "End Time": "11:30:00"},
    {"Session": "Qualifying", "Date": "5-Jul-2025", "Start Time": "14:00:00", "End Time": "15:00:00"},
    {"Session": "GRAND PRIX (52 LAPS OR 120 MINS)", "Date": "6-Jul-2025", "Start Time": "14:00:00", "End Time": "15:00:00"}
]


@qc_router.post("/early-warning1")
async def generate_timeline_only(bsa_file: UploadFile = File(...)):
    try:
        contents = await bsa_file.read()
        
        # 1. READ THE CORRECT SHEET & FIND HEADERS
        # Try to read the specific "Worksheet" tab. If it fails, fallback to the first tab (0).
        try:
            df_raw = pd.read_excel(io.BytesIO(contents), sheet_name="Worksheet", header=None, nrows=30)
            target_sheet = "Worksheet"
        except ValueError:
            df_raw = pd.read_excel(io.BytesIO(contents), sheet_name=0, header=None, nrows=30)
            target_sheet = 0

        header_idx = 5  # Default fallback
        
        for i, row in df_raw.iterrows():
            # Convert row to a single lowercase string to easily search for keywords
            row_str = " ".join([str(val).lower() for val in row.values if pd.notna(val)])
            
            # If a row contains BOTH 'market' and 'date', it's definitely the header row
            if 'market' in row_str and 'date' in row_str:
                header_idx = i
                print(f"🎯 SUCCESS: Found headers on row index {header_idx} of sheet '{target_sheet}'")
                break
                
        # Read the dataframe using the perfectly detected row and sheet
        df = pd.read_excel(io.BytesIO(contents), sheet_name=target_sheet, header=header_idx)
        
        # CLEANUP: Remove hidden newlines, carriage returns, and double spaces from column names
        df.columns = df.columns.astype(str).str.replace('\n', ' ').str.replace('\r', '').str.strip()
        df.columns = [" ".join(col.split()) for col in df.columns]

        # 2. SMART COLUMN MAPPING
        col_date_utc = next((col for col in df.columns if 'date' in col.lower() and 'utc' in col.lower()), None)
        col_start_utc = next((col for col in df.columns if 'start' in col.lower() and 'utc' in col.lower()), None)
        col_end_utc = next((col for col in df.columns if 'end' in col.lower() and 'utc' in col.lower()), None)
        
        # Local time columns (Exact matches to avoid overlapping with UTC columns)
        col_local_date = next((col for col in df.columns if col.lower() == 'date'), None)
        col_local_start = next((col for col in df.columns if col.lower() == 'start'), None)
        col_local_end = next((col for col in df.columns if col.lower() == 'end'), None)
        
        # Categorical columns
        col_type = next((col for col in df.columns if 'type of program' in col.lower()), None)
        col_market = next((col for col in df.columns if 'market' in col.lower()), None)
        col_channel = next((col for col in df.columns if 'channel' in col.lower()), None)
        col_comp = next((col for col in df.columns if 'competition' in col.lower()), None)

        if not all([col_date_utc, col_start_utc, col_end_utc]):
            raise HTTPException(status_code=400, detail=f"Missing UTC Date/Time columns. Found headers: {df.columns.tolist()}")

        # Standardize column names for React
        rename_map = {}
        if col_market: rename_map[col_market] = 'Market'
        if col_channel: rename_map[col_channel] = 'TV-Channel'
        if col_comp: rename_map[col_comp] = 'Competition'
        if col_type: rename_map[col_type] = 'Type of program'
        df = df.rename(columns=rename_map)

        # 3. X-AXIS DATETIME LOGIC (Strictly UTC for chart alignment)
        df['Start_Datetime'] = pd.to_datetime(df[col_date_utc].astype(str) + ' ' + df[col_start_utc].astype(str), errors='coerce')
        df['End_Datetime'] = pd.to_datetime(df[col_date_utc].astype(str) + ' ' + df[col_end_utc].astype(str), errors='coerce')
        df = df.dropna(subset=['Start_Datetime', 'End_Datetime'])

        # 4. EXTRACTION FOR TOOLTIPS: Grab the Local Market Times
        if col_local_date and col_local_start and col_local_end:
            df['Local_Start_Str'] = df[col_local_date].astype(str) + ' ' + df[col_local_start].astype(str)
            df['Local_End_Str'] = df[col_local_date].astype(str) + ' ' + df[col_local_end].astype(str)
        else:
            df['Local_Start_Str'] = "Unknown"
            df['Local_End_Str'] = "Unknown"

        # 5. FILTER PROGRAM TYPES
        df_live = df.copy()

        # 6. CONVERT DATETIMES TO ISO
        if not df_live.empty:
            df_live['Start_Datetime'] = df_live['Start_Datetime'].dt.strftime('%Y-%m-%dT%H:%M:%S')
            df_live['End_Datetime'] = df_live['End_Datetime'].dt.strftime('%Y-%m-%dT%H:%M:%S')
        df_live = df_live.fillna("")

        # 7. PROCESS OFFICIAL SCHEDULE
        official_schedule_processed = []
        for item in HARDCODED_SCHEDULE:
            start_dt = pd.to_datetime(f"{item['Date']} {item['Start Time']}").strftime('%Y-%m-%dT%H:%M:%S')
            end_dt = pd.to_datetime(f"{item['Date']} {item['End Time']}").strftime('%Y-%m-%dT%H:%M:%S')
            official_schedule_processed.append({
                "Session": item["Session"],
                "Start_Datetime": start_dt,
                "End_Datetime": end_dt
            })

        return {
            "timeline_view": json.loads(df_live.to_json(orient="records", date_format="iso")),
            "official_schedule": official_schedule_processed
        }

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# Initialize Google Sheets 
# Initialize Google Sheets 
gc = gspread.oauth(
    credentials_filename='client_secrets.json',     
    authorized_user_filename='authorized_user.json' 
)
SHEET_ID = "1Sufswj10ntTAfFrjc4WGOxDswR5oHyakvVdsXyps91U"

@qc_router.get("/delivery-analytics")
def get_delivery_dashboard_data():
    sh = gc.open_by_key(SHEET_ID)
    worksheet = sh.worksheet("Overview")
    
    raw_data = worksheet.get_all_values()
    
    if not raw_data or len(raw_data) < 2:
        return []

    # 🧹 MAGIC FIX 1: SMART HEADER DETECTION
    # Scan the first 20 rows to find where the actual headers start
    header_row_index = 0
    for i, row in enumerate(raw_data[:20]):
        # If this row contains our core ID columns, it's the real header row!
        if "ROSCO ID" in row or "Delivery ID" in row:
            header_row_index = i
            break

    # Clean the actual header row
    raw_headers = raw_data[header_row_index]
    headers = [re.sub(r'\s+', ' ', str(h)).strip() for h in raw_headers]
    
    # The data rows are everything AFTER the header row
    rows = raw_data[header_row_index + 1:]

    print(f"\n✅ FOUND HEADERS ON ROW {header_row_index + 1}")
    print(f"✅ FOUND {len(rows)} ROWS OF DATA")

    formatted_payload = []
    
    # --- HELPER FUNCTIONS FOR GOOGLE SHEETS DATA ---
    def safe_int(value):
        if not value: return 0
        val_str = str(value).strip().replace(',', '')
        if val_str in ['-', 'N/A', '', 'None', '#N/A']: return 0
        try:
            return int(float(val_str))
        except ValueError:
            return 0
            
    def safe_float(value):
        if not value: return 0.0
        val_str = str(value).strip().replace('%', '').replace(',', '')
        if val_str in ['-', 'N/A', '', 'None', '#N/A', '#REF!']: return 0.0
        try:
            return float(val_str)
        except ValueError:
            return 0.0
    
    def gms_parse_date(date_str):
        if not date_str or date_str in ['-', 'N/A', '', 'None']: return None
        try:
            # Adjust format if your sheet uses DD/MM/YYYY or MM/DD/YYYY
            return datetime.strptime(str(date_str).strip(), '%Y-%m-%d')
        except:
            return None
    # -----------------------------------------------

    for row in rows:
        row_dict = dict(zip(headers, row))

        # 🛑 EXCLUDE RR JOBS
        if row_dict.get('Job') == 'RR':
            continue

        # 🛑 KEEP ONLY 'CONFIRMED' ROSCO STATUS
        rosco_status_raw = str(row_dict.get('Rosco Status', '')).strip().lower()
        if rosco_status_raw != 'confirmed':
            continue

        # Logic for SLA Met (Original vs Delivered)
        original_date = gms_parse_date(row_dict.get('Original Delivery Date'))
        delivered_date = gms_parse_date(row_dict.get('Delivered Date'))
        
        sla_met = False
        if original_date and delivered_date:
            sla_met = delivered_date <= original_date
        elif original_date and not delivered_date:
            sla_met = False # Not delivered yet, so not met
        
        # 🧠 MAGIC FIX 2: Handle Negative Delays
        delay_raw = safe_int(row_dict.get('Delay in days', 0))
        delay_severity = abs(delay_raw) if delay_raw < 0 else 0

        error_val = safe_float(row_dict.get('Error %', 0))
        expected_effort = safe_float(row_dict.get('Expected Effort', 0))
        actual_spent = safe_float(row_dict.get('Actual Spent', 0))

        item = {
            "tracking_id": row_dict.get('ROSCO ID', ''),
            "delivery_uid": row_dict.get('Delivery ID', ''),
            "client_account": row_dict.get('Product/Client', ''),
            "description_text": row_dict.get('Description', ''),
            "owner_fte": row_dict.get('FTE', ''),
            "office_location": row_dict.get('Office', ''),
            "sport_category": row_dict.get('Sport', ''),
            "target_date": row_dict.get('Best Expected Date', ''),
            "delivery_status": row_dict.get('Delivery Status', ''),
            "delay_severity": delay_severity, 
            "is_backlog": 1 if row_dict.get('transition') == 'backlog' else 0,
            
            "POC": row_dict.get('POC', ''),
            "Rework (Yes/No)": row_dict.get('Rework (Yes/No)', ''),
            "Expected Effort": expected_effort,
            "Actual Spent": actual_spent,
            "Delivery Detail": row_dict.get('Delivery Detail', ''),
            "Assignment status": row_dict.get('Assignment status', ''),
            "Delivery Delay Reason": row_dict.get('Delivery Delay Reason', ''),
            "Rework Reason": row_dict.get('Rework Reason', ''),
            "Job": row_dict.get('Job', ''),
            
            "Monitoring Start Date": row_dict.get('Monitoring Start Date', ''),
            "Monitoring End Date": row_dict.get('Monitoring End Date', ''),
            "Original Delivery Date": row_dict.get('Original Delivery Date', ''),
            "Rework Postponement Date": row_dict.get('Rework Postponement Date', ''),
            "Delivered Date": row_dict.get('Delivered Date', ''),
            "Final Delivery Date": row_dict.get('Final Delivery Date', ''),
            
            "original_delivery_date": row_dict.get('Original Delivery Date', ''),
            "rosco_status": row_dict.get('Rosco Status', ''),
            "actual_delivered_date": row_dict.get('Delivered Date', ''),
            "sla_status": "MET" if sla_met else "MISSED",

            "delivery_metrics": {
                "Workload": {
                    "Total_Evaluated": safe_int(row_dict.get('Total Lines', 0)),
                    "Passed": safe_int(row_dict.get('In Scope', 0)),
                    "Failed": safe_int(row_dict.get('Out Of Scope', 0)),
                },
                "Accuracy": {
                    "Total_Evaluated": 100,
                    "Passed": 100 - error_val,
                    "Failed": error_val,
                }
            }
        }
        formatted_payload.append(item)

    return formatted_payload