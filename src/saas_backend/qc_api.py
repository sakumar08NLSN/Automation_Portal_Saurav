# from fastapi import FastAPI, Query, UploadFile, File, HTTPException, Form
# from fastapi.responses import FileResponse, JSONResponse
# from contextlib import asynccontextmanager
# import pandas as pd 
# import os
# import time
# import threading
# import shutil # Used for efficient file saving
# from typing import Optional, List # Added List for checks
# from C_data_processing import DataExplorer
# from io import BytesIO # Needed to save Excel in memory before returning

# # --- Data/Project Specific Imports ---
# # import pathlib
# # from constants import DATA_PATH 
# # from data_processing import DataExplorer # Assuming this is imported

# # --- QC Specific Imports ---
# from qc_checks import (
#     # ... (Your original QC imports) ...
#     detect_period_from_rosco,
#     load_bsr,
#     period_check,
#     completeness_check,
#     overlap_duplicate_daybreak_check,
#     program_category_check,
#     duration_check,
#     check_event_matchday_competition,
#     market_channel_program_duration_check,
#     domestic_market_coverage_check,
#     rates_and_ratings_check,
#     duplicated_markets_check,
#     country_channel_id_check,
#     client_lstv_ott_check,
#     color_excel,
#     generate_summary_sheet,
#     # Placeholder for a function that handles all market checks
#     # You would replace this with actual logic in qc_checks.py
#     # market_specific_check_processor,
# )

# from C_data_processing_f1 import ( 
#     BSRValidator, 
#     color_excel,
#     generate_summary_sheet,
# )

# # -------------------- ⚙️ Folder setup --------------------
# BASE_DIR = os.getcwd()
# UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
# OUTPUT_FOLDER = os.path.join(BASE_DIR, "outputs")
# os.makedirs(UPLOAD_FOLDER, exist_ok=True)
# os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# # -------------------- 🧹 Cleanup Functions --------------------
# def cleanup_old_files(folder_path, max_age_minutes=30):
#     """Deletes files older than max_age_minutes."""
#     now = time.time()
#     max_age_seconds = max_age_minutes * 60

#     for filename in os.listdir(folder_path):
#         file_path = os.path.join(folder_path, filename)
#         if os.path.isfile(file_path):
#             file_age = now - os.path.getmtime(file_path)
#             if file_age > max_age_seconds:
#                 try:
#                     os.remove(file_path)
#                     print(f"🧹 Deleted old file: {file_path}")
#                 except Exception as e:
#                     print(f"⚠️ Error deleting {file_path}: {e}")

# def start_background_cleanup():
#     """Starts a background thread that cleans up old files every 5 minutes."""
#     def run_cleanup():
#         while True:
#             cleanup_old_files(UPLOAD_FOLDER, max_age_minutes=30)
#             cleanup_old_files(OUTPUT_FOLDER, max_age_minutes=30)
#             time.sleep(300)

#     thread = threading.Thread(target=run_cleanup, daemon=True)
#     thread.start()
# # -----------------------------------------------------------

# # Start the cleanup thread
# start_background_cleanup()

# # -------------------- 🧠 FastAPI Setup and Lifespan --------------------

# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     # This is your existing lifespan logic, ensuring the Laligadata is loaded
#     try:
#         # app.state.df = pd.read_csv(DATA_PATH / "Sales.csv" , index_col=0 , parse_dates= True)
#         app.state.df = pd.DataFrame() # Placeholder if Sales.csv isn't available
#     except Exception as e:
#         print(f"Warning: Could not load Sales.csv during startup: {e}")
#         app.state.df = pd.DataFrame() # Ensure state exists
        
#     yield
#     # Cleanup state
#     del app.state.df

# app = FastAPI(lifespan=lifespan)

# # -------------------- 📂 Original API Endpoints --------------------

# @app.post("/api/upload_csv")
# async def upload_csv(file: UploadFile = File(...)):
#     """
#     Handles CSV file upload from the frontend and saves it to the data directory.
#     """
#     file_location = os.path.join(UPLOAD_FOLDER, file.filename) 
    
#     try:
#         with open(file_location, "wb") as buffer:
#             shutil.copyfileobj(file.file, buffer)
            
#         app.state.df = pd.read_csv(file_location, index_col=0, parse_dates=True)

#         return {"filename": file.filename, "detail": f"File successfully uploaded and saved to {file_location}"}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"An error occurred during file upload: {e}")
#     finally:
#         await file.close()

# # -------------------- 📂 End Points Using DataExplorer Class --------------------

# @app.get("/api/summary")
# async def read_summary_data():
#     if app.state.df.empty:
#         raise HTTPException(status_code=404, detail="Data not loaded. Upload Sales.csv first.")
#     data = DataExplorer(app.state.df)
#     return data.summary().json_response()

# @app.get("/api/kpis")
# async def read_kpis(country: str = Query(None)):
#     if app.state.df.empty:
#         raise HTTPException(status_code=404, detail="Data not loaded. Upload Sales.csv first.")
#     data = DataExplorer(app.state.df)
#     return data.kpis(country)

# @app.get("/api/")
# async def read_sales(limit: int = Query(100, gt=0, lt=150000)):
#     if app.state.df.empty:
#         raise HTTPException(status_code=404, detail="Data not loaded. Upload Sales.csv first.")
#     data = DataExplorer(app.state.df, limit)
#     return data.json_response()

# # -------------------- 🚀 FULL QC API Endpoint Using C_data_processing.py --------------------

# @app.post("/api/run_qc")
# async def run_qc_checks(
#     rosco_file: UploadFile = File(..., description="The Rosco file (.xlsx)"),
#     bsr_file: UploadFile = File(..., description="The BSR file (.xlsx)"),
#     data_file: Optional[UploadFile] = File(None, description="The optional Client Data file (.xlsx)")
# ):
#     """
#     Runs the full QC pipeline on the uploaded Rosco, BSR, and optional Data files 
#     and returns the processed Excel file.
#     """
    
#     # Define paths for uploaded files
#     rosco_path = os.path.join(UPLOAD_FOLDER, rosco_file.filename)
#     bsr_path = os.path.join(UPLOAD_FOLDER, bsr_file.filename)
#     data_path = None

#     try:
#         # 1. Save uploaded files to disk (for path-based QC functions)
#         with open(rosco_path, "wb") as buffer:
#             shutil.copyfileobj(rosco_file.file, buffer)
#         with open(bsr_path, "wb") as buffer:
#             shutil.copyfileobj(bsr_file.file, buffer)
        
#         df_data = None
#         if data_file and data_file.filename:
#             data_path = os.path.join(UPLOAD_FOLDER, data_file.filename)
#             with open(data_path, "wb") as buffer:
#                 shutil.copyfileobj(data_file.file, buffer)
#             df_data = pd.read_excel(data_path) 

#         # 2. Run QC Pipeline 
#         start_date, end_date = detect_period_from_rosco(rosco_path)
#         df = load_bsr(bsr_path)

#         df = period_check(df, start_date, end_date)
#         df = completeness_check(df)
#         df = overlap_duplicate_daybreak_check(df)
#         df = program_category_check(df)
#         df = duration_check(df)

#         # Handle optional data file logic
#         df = check_event_matchday_competition(df, df_data=df_data, rosco_path=rosco_path)
#         df = market_channel_program_duration_check(df, reference_df=df_data)
#         df = domestic_market_coverage_check(df, reference_df=df_data)

#         df = rates_and_ratings_check(df)
#         df = duplicated_markets_check(df)
#         df = country_channel_id_check(df)
#         df = client_lstv_ott_check(df)

#         # 3. Generate Output File on Disk (in OUTPUT_FOLDER)
#         output_file = f"QC_Result_{os.path.splitext(bsr_file.filename)[0]}.xlsx"
#         output_path = os.path.join(OUTPUT_FOLDER, output_file)

#         df.to_excel(output_path, index=False)
#         color_excel(output_path, df)
#         generate_summary_sheet(output_path, df)

#         # 4. Return FileResponse
#         return FileResponse(
#             path=output_path,
#             filename=output_file,
#             media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
#         )

#     except Exception as e:
#         print(f"QC Error: {e}")
#         # Clean up any input files that might have been partially written
#         for path in [rosco_path, bsr_path, data_path]:
#             if path and os.path.exists(path):
#                 os.remove(path)
                
#         raise HTTPException(status_code=500, detail=f"An error occurred during QC processing: {str(e)}")
#     finally:
#         # Ensure all file streams are closed
#         await rosco_file.close()
#         await bsr_file.close()
#         if data_file:
#             await data_file.close()


# # -------------------- 🌍 NEW MARKET SPECIFIC CHECK ENDPOINT that is using market_specific_check_processor  --------------------

# # -------------------- 🌍 NEW MARKET SPECIFIC CHECK ENDPOINT (FIXED) --------------------
# # -------------------- 🌍 NEW MARKET SPECIFIC CHECK ENDPOINT (MODIFIED) --------------------
# @app.post("/api/market_check_and_process", response_model=None)
# async def market_check_and_process(
#     # BSR file (mandatory)
#     bsr_file: UploadFile = File(..., description="BSR file for market-specific checks"),
#     # Obligation file (optional, for F1 check)
#     obligation_file: Optional[UploadFile] = File(None, description="F1 Obligation file for broadcaster checks"), 
#     # NEW: Overnight file (optional, for Audience Update)
#     overnight_file: Optional[UploadFile] = File(None, description="Overnight Audience file for upscale/integrity check"), # <-- NEW PARAMETER
#     # List of checks to run
#     checks: List[str] = Form(..., description="List of selected check keys (e.g., 'remove_andorra')")
# ):
#     """
#     Applies selected market-specific checks and transformations to the BSR file.
#     It returns a JSON summary and a URL for file download.
#     """
    
#     bsr_file_path = os.path.join(UPLOAD_FOLDER, bsr_file.filename)
#     obligation_path = None
#     overnight_path = None # <-- NEW PATH VARIABLE
    
#     # Generate a unique output filename that the frontend can use for download
#     output_filename = f"Processed_BSR_{os.path.splitext(bsr_file.filename)[0]}_{int(time.time())}.xlsx"
#     output_path = os.path.join(OUTPUT_FOLDER, output_filename)
    
#     try:
#         # 1. Save uploaded BSR file temporarily
#         with open(bsr_file_path, "wb") as buffer:
#             shutil.copyfileobj(bsr_file.file, buffer)
            
#         # 2. Save optional Obligation file
#         if obligation_file and obligation_file.filename:
#             obligation_path = os.path.join(UPLOAD_FOLDER, obligation_file.filename)
#             with open(obligation_path, "wb") as buffer:
#                 shutil.copyfileobj(obligation_file.file, buffer)
#             print(f"Saved obligation file to: {obligation_path}")

#         # 3. Save optional Overnight file
#         if overnight_file and overnight_file.filename: # <-- NEW LOGIC
#             overnight_path = os.path.join(UPLOAD_FOLDER, overnight_file.filename)
#             with open(overnight_path, "wb") as buffer:
#                 shutil.copyfileobj(overnight_file.file, buffer)
#             print(f"Saved overnight file to: {overnight_path}")


#         # 4. Initialize Validator (Pass ALL optional paths here)
#         validator = BSRValidator(
#             bsr_path=bsr_file_path, 
#             obligation_path=obligation_path, 
#             overnight_path=overnight_path # <-- PASSING NEW PATH
#         ) 

#         # 5. Apply selected checks and capture the list of structured summaries
#         status_summaries = validator.market_check_processor(checks)
        
#         # 6. Access and save the modified DataFrame
#         df_processed = validator.df
        
#         # ... (File saving, JSON response, and error handling remain the same) ...

#         # 7. Construct the download URL and return the JSON response
#         clean_summaries = [s for s in status_summaries if isinstance(s, dict)]
#         if df_processed.empty:
#              raise Exception("Processed DataFrame is empty after applying checks.")

#         df_processed.to_excel(output_path, index=False)
#         download_url = f"/api/download_file?filename={output_filename}" 

#         return JSONResponse(content={
#             "status": "Success",
#             "message": f"Successfully applied {len(checks)} market checks. Processed file is ready for download.",
#             "download_url": download_url,
#             "summaries": clean_summaries
#         })

#     except Exception as e:
#         print(f"Market Check Error: {e}")
#         raise HTTPException(status_code=500, detail=f"An error occurred during market checks: {str(e)}")
#     finally:
#         # Ensure file streams are closed and cleanup is run
#         await bsr_file.close()
#         if obligation_file:
#             await obligation_file.close()
#         if overnight_file: # <-- CLOSE NEW STREAM
#             await overnight_file.close()
            
#         # IMPORTANT: Clean up uploaded source files immediately
#         for path in [bsr_file_path, obligation_path, overnight_path]: # <-- ADD NEW PATH TO CLEANUP
#             if path and os.path.exists(path):
#                 os.remove(path)


# # -------------------- 📥 NEW DOWNLOAD ENDPOINT --------------------
# # This endpoint handles the actual file retrieval requested via the download_url.

# @app.get("/api/download_file")
# async def download_file(filename: str = Query(...)):
#     """Retrieves a previously generated file from the output folder."""
#     file_path = os.path.join(OUTPUT_FOLDER, filename)
    
#     if not os.path.exists(file_path):
#         # This will be triggered if the cleanup thread deleted the file, or if the filename is bad
#         raise HTTPException(status_code=404, detail="File not found or link has expired.")
        
#     return FileResponse(
#         path=file_path,
#         filename=filename,
#         media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
#     )


from fastapi import APIRouter, FastAPI, Query, UploadFile, File, HTTPException, Form
from fastapi.responses import FileResponse, JSONResponse
from contextlib import asynccontextmanager
import pandas as pd 
import os
import time
import threading
import shutil
from typing import Optional, List
from C_data_processing import DataExplorer
from io import BytesIO
import json

# --- QC Specific Imports ---
from qc_checks import (
    detect_period_from_rosco,
    load_bsr,
    period_check,
    completeness_check,
    overlap_duplicate_daybreak_check,
    program_category_check,
    duration_check,
    check_event_matchday_competition,
    market_channel_program_duration_check,
    domestic_market_coverage_check,
    rates_and_ratings_check,
    duplicated_markets_check,
    country_channel_id_check,
    client_lstv_ott_check,
    color_excel,
    generate_summary_sheet,
)

from C_data_processing_f1 import ( 
    BSRValidator, 
    color_excel,
    generate_summary_sheet,
)

MOCK_QC_SUMMARY = [
    {"id": 1, "description": "Period Integrity Check", "action": "Audit", "status": "Completed", "total_issues_flagged": 0},
    {"id": 2, "description": "Field Completeness Check", "action": "Audit", "status": "Issue Found", "total_issues_flagged": 15},
    # ... rest of your mock data
]
# -------------------- ⚙️ Folder setup --------------------
BASE_DIR = os.getcwd()
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
OUTPUT_FOLDER = os.path.join(BASE_DIR, "outputs")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# -------------------- 🧹 Cleanup Functions --------------------
def cleanup_old_files(folder_path, max_age_minutes=30):
    """Deletes files older than max_age_minutes."""
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
    """Starts a background thread that cleans up old files every 5 minutes."""
    def run_cleanup():
        while True:
            cleanup_old_files(UPLOAD_FOLDER, max_age_minutes=30)
            cleanup_old_files(OUTPUT_FOLDER, max_age_minutes=30)
            time.sleep(300)

    thread = threading.Thread(target=run_cleanup, daemon=True)
    thread.start()
# -----------------------------------------------------------

# Start the cleanup thread
start_background_cleanup()

# -------------------- 🧠 FastAPI Setup and Lifespan --------------------
# NOTE: The lifespan context must be handled by the main application (master_app) 
# or passed to the router via dependencies if state is required. 

# 💡 CHANGE: Convert FastAPI app to APIRouter
router = APIRouter()

# -------------------- 📂 Original API Endpoints --------------------
# 💡 CHANGE: Replace @app.post/get with @router.post/get and remove /api prefixes

@router.post("/upload_csv")
async def upload_csv(file: UploadFile = File(...)):
    """Handles CSV file upload from the frontend and saves it to the data directory."""
    file_location = os.path.join(UPLOAD_FOLDER, file.filename) 
    
    try:
        # Accessing app.state inside a router requires state to be passed or accessed via request.
        # For simplicity, we assume this endpoint mainly handles file storage for now.
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # NOTE: If app.state is critical, this logic must be moved to dashboard_router or injected.
        # We comment out the app.state line to avoid breaking the router conversion.
        # app.state.df = pd.read_csv(file_location, index_col=0, parse_dates=True) 

        return {"filename": file.filename, "detail": f"File successfully uploaded and saved to {file_location}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred during file upload: {e}")
    finally:
        await file.close()

# -------------------- 📂 End Points Using DataExplorer Class --------------------

# NOTE: These endpoints require app.state.df, which cannot be accessed directly in a standalone router.
# This logic should ideally be moved to a function/file accessible by dashboard_router.
# For simplicity, we define the routes but keep the logic requiring app.state commented out.

@router.get("/summary")
async def read_summary_data():
    # if app.state.df.empty: raise HTTPException(...)
    # data = DataExplorer(app.state.df)
    # return data.summary().json_response()
    return {"detail": "Summary data logic pending full state integration."}


@router.get("/kpis")
async def read_kpis(country: str = Query(None)):
    # if app.state.df.empty: raise HTTPException(...)
    # data = DataExplorer(app.state.df)
    # return data.kpis(country)
    return {"detail": "KPI logic pending full state integration."}


@router.get("/")
async def read_sales(limit: int = Query(100, gt=0, lt=150000)):
    # if app.state.df.empty: raise HTTPException(...)
    # data = DataExplorer(app.state.df, limit)
    # return data.json_response()
    return {"detail": "Sales logic pending full state integration."}


# -------------------- 🚀 FULL QC API Endpoint Using C_data_processing.py --------------------

@router.post("/run_qc")
async def run_qc_checks(
    rosco_file: UploadFile = File(..., description="The Rosco file (.xlsx)"),
    bsr_file: UploadFile = File(..., description="The BSR file (.xlsx)"),
    data_file: Optional[UploadFile] = File(None, description="The optional Client Data file (.xlsx)")
):
    # ... (QC logic remains, ensure you use local paths for the QC functions) ...
    
    # Define paths for uploaded files
    rosco_path = os.path.join(UPLOAD_FOLDER, rosco_file.filename)
    bsr_path = os.path.join(UPLOAD_FOLDER, bsr_file.filename)
    data_path = None

    try:
        # 1. Save uploaded files to disk (for path-based QC functions)
        with open(rosco_path, "wb") as buffer:
            shutil.copyfileobj(rosco_file.file, buffer)
        with open(bsr_path, "wb") as buffer:
            shutil.copyfileobj(bsr_file.file, buffer)
        
        df_data = None
        if data_file and data_file.filename:
            data_path = os.path.join(UPLOAD_FOLDER, data_file.filename)
            with open(data_path, "wb") as buffer:
                shutil.copyfileobj(data_file.file, buffer)
            df_data = pd.read_excel(data_path) 

        # 2. Run QC Pipeline 
        start_date, end_date = detect_period_from_rosco(rosco_path)
        df = load_bsr(bsr_path)

        df = period_check(df, start_date, end_date)
        df = completeness_check(df)
        df = overlap_duplicate_daybreak_check(df)
        df = program_category_check(df)
        df = duration_check(df)
        df = check_event_matchday_competition(df, df_data=df_data, rosco_path=rosco_path)
        df = market_channel_program_duration_check(df, reference_df=df_data)
        df = domestic_market_coverage_check(df, reference_df=df_data)
        df = rates_and_ratings_check(df)
        df = duplicated_markets_check(df)
        df = country_channel_id_check(df)
        df = client_lstv_ott_check(df)

        # 3. Generate Output File on Disk (in OUTPUT_FOLDER)
        output_file = f"QC_Result_{os.path.splitext(bsr_file.filename)[0]}.xlsx"
        output_path = os.path.join(OUTPUT_FOLDER, output_file)

        df.to_excel(output_path, index=False)
        color_excel(output_path, df)
        generate_summary_sheet(output_path, df)

        # 💡 Extract the Summary Data (MOCK/Real Logic Needed Here)
        # Since the backend usually generates this summary table, we need to extract it.
        # TEMPORARY MOCK FOR SUMMARY DATA (You would replace this with actual logic):
        summary_data = [
    # 🚨 FIX 1: Use a dictionary structure instead of QcSummaryResult()
                {
                    "id": 1, 
                    "description": "Period Integrity Check", 
                    "action": "Audit", 
                    "status": "Completed", 
                    "total_issues_flagged": 0
                },
                {
                    "id": 2, 
                    "description": "Field Completeness Check", 
                    "action": "Audit", 
                    "status": "Issue Found", 
                    "total_issues_flagged": 15
                },
                # ... and so on
            ]

        # 4. Return JSON Response with Download URL
        download_url =  f"/api/qc/download_file?filename={output_file}"

        # 4. Return FileResponse
        # return QcRunResponse(
        #     status="Success",
        #     message="QC checks complete. File ready for download.",
        #     download_url=download_url,
        #     summaries=summary_data # Return the summary data for the frontend table
        # )

        return JSONResponse(content={
            "status": "Success",
            "message": "QC checks complete. File ready for download.",
            "download_url": download_url,
            "summaries": summary_data # List of dictionaries
        })

    except Exception as e:
        print(f"QC Error: {e}")
        for path in [rosco_path, bsr_path, data_path]:
            if path and os.path.exists(path):
                os.remove(path)
        raise HTTPException(status_code=500, detail=f"An error occurred during QC processing: {str(e)}")
    finally:
        await rosco_file.close()
        await bsr_file.close()
        if data_file: await data_file.close()


# -------------------- 🌍 NEW MARKET SPECIFIC CHECK ENDPOINT --------------------

@router.post("/market_check_and_process") # response_model removed for simplicity
async def market_check_and_process(
    bsr_file: UploadFile = File(..., description="BSR file for market-specific checks", alias="bsr_file"),
    obligation_file: Optional[UploadFile] = File(None, description="F1 Obligation file", alias="obligation_file"), 
    overnight_file: Optional[UploadFile] = File(None, description="Overnight Audience file", alias="overnight_file"),
    # 🚨 FIX 1: Set type hint to STR to correctly receive the JSON string from JSON.stringify()
    checks: str = Form(..., alias="checks", description="JSON list of check keys to run")
):
    
    bsr_file_path = os.path.join(UPLOAD_FOLDER, bsr_file.filename)
    obligation_path = None
    overnight_path = None 
    
    output_filename = f"Processed_BSR_{os.path.splitext(bsr_file.filename)[0]}_{int(time.time())}.xlsx"
    output_path = os.path.join(OUTPUT_FOLDER, output_filename)
    
    # 🚨 FIX 2: Explicitly parse the JSON string immediately
    try:
        # Convert the incoming JSON string into a Python list
        checks_list_to_process: List[str] = json.loads(checks)
    except Exception as e:
        # Handle if the input was not a valid JSON array string
        raise HTTPException(status_code=400, detail=f"Invalid check list format: Expected JSON string, got {type(checks)}. Error: {e}")
    
    # 🚨 FIX 3: Check if the list is empty after parsing
    if not checks_list_to_process:
        raise HTTPException(status_code=400, detail="No checks were selected or passed.")
    
    # 🚨 DEBUGGING: This print statement shows the correctly parsed list
    print(f"Final checks list passed to validator: {checks_list_to_process}")

    try:
        # 1. Save Files
        with open(bsr_file_path, "wb") as buffer: shutil.copyfileobj(bsr_file.file, buffer)
        if obligation_file and obligation_file.filename:
            obligation_path = os.path.join(UPLOAD_FOLDER, obligation_file.filename)
            with open(obligation_path, "wb") as buffer: shutil.copyfileobj(obligation_file.file, buffer)
        if overnight_file and overnight_file.filename:
            overnight_path = os.path.join(UPLOAD_FOLDER, overnight_file.filename)
            with open(overnight_path, "wb") as buffer: shutil.copyfileobj(overnight_file.file, buffer)

        # 2. Instantiate and Run Validator
        # Assuming BSRValidator is accessible
        validator = BSRValidator(
            bsr_path=bsr_file_path, 
            obligation_path=obligation_path, 
            overnight_path=overnight_path 
        ) 
        
        # 3. Call the processor with the correctly parsed list
        # This list is guaranteed to be ['duration_limits', ...]
        status_summaries = validator.market_check_processor(checks_list_to_process)
        df_processed = validator.df
        
        # 4. Finalize Output
        clean_summaries = [s for s in status_summaries if isinstance(s, dict)]
        if df_processed.empty: raise Exception("Processed DataFrame is empty after applying checks.")

        df_processed.to_excel(output_path, index=False)
        
        # 5. Return Final JSON Response
        download_url = f"/api/qc/download_file?filename={output_filename}" 

        return JSONResponse(content={
            "status": "Success",
            "message": f"Successfully applied {len(checks_list_to_process)} market checks. Processed file is ready for download.",
            "download_url": download_url,
            "summaries": clean_summaries
        })

    except Exception as e:
        print(f"Market Check Error: {e}")
        # Clean up files on error
        for path in [bsr_file_path, obligation_path, overnight_path]:
            if path and os.path.exists(path): os.remove(path)
            
        raise HTTPException(status_code=500, detail=f"An error occurred during market checks: {str(e)}")
    finally:
        # Close file streams and clean up disk files
        if 'bsr_file' in locals() and bsr_file: await bsr_file.close()
        if 'obligation_file' in locals() and obligation_file: await obligation_file.close()
        if 'overnight_file' in locals() and overnight_file: await overnight_file.close()
            
        for path in [bsr_file_path, obligation_path, overnight_path]:
            if path and os.path.exists(path): os.remove(path)

# -------------------- 📥 DOWNLOAD ENDPOINT --------------------
# 💡 NOTE: This endpoint needs to remain outside of the /qc prefix if its called as /api/download_file.
# We will define a separate router for general utility, or rely on dashboard_router for /api.

@router.get("/download_file")
async def download_file(filename: str = Query(...)):
    """Retrieves a previously generated file from the output folder."""
    file_path = os.path.join(OUTPUT_FOLDER, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found or link has expired.")
        
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    
# -------------------- 🌟 FINAL EXPORT 🌟 --------------------
# We export the APIRouter object instead of the FastAPI app instance.
# This router will be included in app/dashboard_routes.py under the /qc prefix.
qc_router = router