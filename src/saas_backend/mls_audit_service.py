import os
import gc
import time
import shutil
import base64
import io
import pandas as pd
import numpy as np
from datetime import datetime

# --- Helper Functions ---
def get_numeric_serial_vectorized(df, date_col, time_col):
    """Calculates Excel-style date serials safely."""
    try:
        dt = pd.to_datetime(df[date_col], dayfirst=True, errors='coerce')
        time_srs = df[time_col].copy().astype(str)
        time_srs = time_srs.str.replace(r'.*1899-12-30\s+', '', regex=True) 
        tm = pd.to_timedelta(time_srs, errors='coerce')
        time_decs = tm.dt.total_seconds() / 86400.0
        base_date = pd.Timestamp('1899-12-30')
        date_ints = (dt - base_date).dt.days
        return (date_ints + time_decs.fillna(0)).round(4)
    except Exception as e:
        return np.nan

def get_regional_fixtures(file_path):
    """Scans the USA/Canada raw files and extracts all Fixture names for National Checks."""
    try:
        xl = pd.ExcelFile(file_path, engine='calamine')
        df = pd.read_excel(xl, sheet_name=0, skiprows=5)
        xl.close()
        
        fix_col = next((c for c in df.columns if 'Fixture' in str(c) or 'Episode Desc' in str(c)), None)
        if fix_col:
            return set(df[fix_col].dropna().astype(str).str.strip())
    except Exception:
        pass
    return set()

def prep_regional_data(file_path):
    """Extracts Data, applies dynamic 20-min rolling simulcast/spillover logic, and prepares for matching."""
    logs = []
    xl = pd.ExcelFile(file_path, engine='calamine')
    df_raw = pd.read_excel(xl, sheet_name=0, skiprows=5)
    xl.close()

    col_chan = next((c for c in df_raw.columns if 'TV-Channel' in str(c)), df_raw.columns[4])
    col_date = next((c for c in df_raw.columns if c == 'Date'), df_raw.columns[8])
    
    # TIP: If your MLS data is in UTC time, change 'Start' below to 'Start (UTC)' to fix time mismatches!
    col_time = next((c for c in df_raw.columns if c == 'Start'), df_raw.columns[12])
    col_end = next((c for c in df_raw.columns if c == 'End'), df_raw.columns[13])
    
    col_broadcaster = next((c for c in df_raw.columns if 'Broadcaster' in str(c)), df_raw.columns[3])
    col_title = next((c for c in df_raw.columns if 'Program Title' in str(c)), df_raw.columns[15])
    
    col_aud = next((c for c in df_raw.columns if 'Aud Metered' in str(c) and '3+' in str(c)), None)
    if not col_aud:
        col_aud = next((c for c in df_raw.columns if 'Aud. Estimates' in str(c)), df_raw.columns[28])

    clean_aud_strings = df_raw[col_aud].astype(str).str.replace(',', '.').str.replace(r'[^\d.]', '', regex=True)

    df_clean = pd.DataFrame({
        'broadcaster': df_raw[col_broadcaster].astype(str).str.strip().str.upper(),
        'title': df_raw[col_title].astype(str).str.strip().str.upper(),
        '_join_chan': df_raw[col_chan].astype(str).str.strip().str.upper(),
        '_regional_aud': pd.to_numeric(clean_aud_strings, errors='coerce').fillna(0.0)
    })

    df_clean['_calc_serial'] = get_numeric_serial_vectorized(df_raw, col_date, col_time)
    df_clean = df_clean.dropna(subset=['_calc_serial'])

    base_date = pd.Timestamp('1899-12-30')
    df_clean['start_dt'] = base_date + pd.to_timedelta(df_clean['_calc_serial'], unit='D')

    time_srs_end = df_raw[col_end].copy().astype(str).str.replace(r'.*1899-12-30\s+', '', regex=True)
    end_td = pd.to_timedelta(time_srs_end, errors='coerce')
    df_clean['end_dt'] = base_date + pd.to_timedelta((df_clean['start_dt'] - base_date).dt.days, unit='D') + end_td
    
    df_clean['end_dt'] = df_clean['end_dt'].fillna(df_clean['start_dt'] + pd.Timedelta(hours=2))

    cross_midnight = df_clean['end_dt'] < df_clean['start_dt']
    df_clean.loc[cross_midnight, 'end_dt'] += pd.Timedelta(days=1)

    # --- SAFEST DYNAMIC SIMULCAST & SPILLOVER ENGINE ---
    df_clean = df_clean.sort_values(['broadcaster', 'title', 'start_dt'])

    df_clean['prev_end'] = df_clean.groupby(['broadcaster', 'title'])['end_dt'].shift(1)
    df_clean['is_new_session'] = (df_clean['start_dt'] > (df_clean['prev_end'] + pd.Timedelta(minutes=20)))
    df_clean['is_new_session'] = df_clean['is_new_session'].fillna(True)
    df_clean['session_id'] = df_clean.groupby(['broadcaster', 'title'])['is_new_session'].cumsum()

    session_totals = df_clean.groupby(['broadcaster', 'title', 'session_id'])['_regional_aud'].sum().reset_index(name='session_total_aud')

    df_clean = df_clean.merge(session_totals, on=['broadcaster', 'title', 'session_id'])
    df_clean['_regional_aud'] = df_clean['session_total_aud']

    df_clean = df_clean.sort_values('_calc_serial')
    
    del df_raw
    gc.collect()
    return df_clean, logs

# --- Main Processor ---
async def process_mls_audit_logic_stream(mls_data, usa_data, canada_data, upload_folder):
    timestamp = int(time.time())
    start_time = time.time()
    
    is_windows = os.name == 'nt'
    work_dir = upload_folder if is_windows else "/tmp"
    
    yield f"data: [LOG] MLS Engine Active. OS: {'Windows' if is_windows else 'Linux/ECS'}\n\n"
    
    mls_p = os.path.join(work_dir, f"m_{timestamp}.xlsx")
    usa_p = os.path.join(work_dir, f"u_{timestamp}.xlsx") if usa_data else None
    can_p = os.path.join(work_dir, f"c_{timestamp}.xlsx") if canada_data else None

    # 1. Buffering
    try:
        with open(mls_p, "wb") as f: shutil.copyfileobj(mls_data.file, f)
        if usa_data:
            with open(usa_p, "wb") as f: shutil.copyfileobj(usa_data.file, f)
        if canada_data:
            with open(can_p, "wb") as f: shutil.copyfileobj(canada_data.file, f)
        yield "data: [LOG] Step 1/5: Files safely buffered to disk.\n\n"
    except Exception as e:
        yield f"data: [ERROR] Disk Write Failure: {str(e)}\n\n"
        return

    # 2. Extract Fixtures for US/CAN Checks
    yield "data: [LOG] Step 2/5: Verifying Fixtures in USA & Canada files...\n\n"
    usa_fixtures = get_regional_fixtures(usa_p) if usa_p else set()
    can_fixtures = get_regional_fixtures(can_p) if can_p else set()

    # 3. Load MLS Data & Base Columns
    yield "data: [LOG] Step 3/5: Loading core MLS Data & calculating base columns...\n\n"
    try:
        xl_mls = pd.ExcelFile(mls_p, engine='calamine')
        
        export_sheet = next((s for s in xl_mls.sheet_names if "rates export" in s.lower()), xl_mls.sheet_names[0])
        df_mls = pd.read_excel(xl_mls, sheet_name=export_sheet)
        
        sched_sheet = next((s for s in xl_mls.sheet_names if "schedule" in s.lower()), None)
        df_sched = pd.read_excel(xl_mls, sheet_name=sched_sheet) if sched_sheet else pd.DataFrame()
        
        multi_sheet = next((s for s in xl_mls.sheet_names if "multi" in s.lower() and "rate" in s.lower()), None)
        df_multi = pd.read_excel(xl_mls, sheet_name=multi_sheet) if multi_sheet else pd.DataFrame()
        
        xl_mls.close()

        df_mls['_calc_serial'] = get_numeric_serial_vectorized(df_mls, 'progr. start (date)', 'progr. start (time)')
        df_mls['_calc_serial'] = pd.to_numeric(df_mls['_calc_serial'], errors='coerce').fillna(0)
        df_mls['_join_chan'] = df_mls['channel'].astype(str).str.strip().str.upper()
        
        # --- REGIONAL AFFILIATE MAPPING ---
        affiliate_keywords = ['WFXT', 'KTVU', 'KTTV', 'WNYW'] 
        fox_national_name = 'FOX BROADCASTING COMPANY' 

        bracket_contents = df_mls['_join_chan'].str.extract(r'\((.*?)\)')[0].fillna('')
        is_affiliate = bracket_contents.isin(affiliate_keywords)
        df_mls.loc[is_affiliate, '_join_chan'] = fox_national_name
        
        df_mls['_original_idx'] = df_mls.index
        
        if 'Live Playing Time' in df_mls.columns:
            lpt_td = pd.to_timedelta(df_mls['Live Playing Time'].astype(str).str.replace(r'.*1899-12-30\s+', '', regex=True), errors='coerce')
            df_mls['Column1'] = (lpt_td.dt.total_seconds() / 60.0).round(0)

        df_mls['Audiences (000)'] = 0.0
        df_mls['1sec Nielsen Rate in EUR'] = 0.0
        df_mls['Requested Date'] = np.nan
        df_mls['Delivery Due'] = np.nan
        df_mls['Date Provided'] = np.nan

    except Exception as e:
        yield f"data: [ERROR] Failed to process MLS file: {str(e)}\n\n"
        return

    # 4. Audience Lookups (The Heavy Lifting Engine)
    yield "data: [LOG] Step 4/5: Running dynamic cross-region audience lookups...\n\n"
    
    if usa_p:
        df_usa, usa_logs = prep_regional_data(usa_p)
        usa_mask = df_mls['channel country'].astype(str).str.strip().str.upper() == 'USA'
        mls_usa_subset = df_mls[usa_mask].sort_values('_calc_serial')

        if not mls_usa_subset.empty and not df_usa.empty:
            reg_fox_mask = mls_usa_subset['_join_chan'].str.contains('FOX') & ~mls_usa_subset['_join_chan'].str.contains('SPORTS|DEPORTES')
            
            mls_std = mls_usa_subset[~reg_fox_mask]
            mls_fox = mls_usa_subset[reg_fox_mask]

            if not mls_std.empty:
                merged_std = pd.merge_asof(mls_std, df_usa, on='_calc_serial', by='_join_chan', direction='nearest', tolerance=0.042)
                matched_std = merged_std.dropna(subset=['_regional_aud'])
                df_mls.loc[matched_std['_original_idx'].values, 'Audiences (000)'] = matched_std['_regional_aud'].values

            if not mls_fox.empty:
                fs_usa_data = df_usa[df_usa['_join_chan'].isin(['FOX SPORTS 1 USA', 'FOX SPORTS 2 USA'])].sort_values('_calc_serial')
                if not fs_usa_data.empty:
                    merged_fox = pd.merge_asof(mls_fox, fs_usa_data, on='_calc_serial', direction='nearest', tolerance=0.042)
                    matched_fox = merged_fox.dropna(subset=['_regional_aud'])
                    df_mls.loc[matched_fox['_original_idx'].values, 'Audiences (000)'] = matched_fox['_regional_aud'].values

        del df_usa
        gc.collect()

    if can_p:
        df_can, can_logs = prep_regional_data(can_p)
        can_mask = df_mls['channel country'].astype(str).str.strip().str.upper() == 'CANADA'
        if not df_mls[can_mask].empty and not df_can.empty:
            merged_can = pd.merge_asof(df_mls[can_mask].sort_values('_calc_serial'), df_can, on='_calc_serial', by='_join_chan', direction='nearest', tolerance=0.042)
            matched_can = merged_can.dropna(subset=['_regional_aud'])
            df_mls.loc[matched_can['_original_idx'].values, 'Audiences (000)'] = matched_can['_regional_aud'].values
        del df_can
        gc.collect()

    # 5. Process Lookups (Rates, Checks, QC, Simulcasts)
    yield "data: [LOG] Step 5/5: Calculating Rates, Checks, and Formatting Output...\n\n"
    if not df_sched.empty and 'Fixture' in df_mls.columns:
        try:
            # Extract Col A(0), M(12), N(13), AD(29), AF(31), AH(33) for financial calculations
            df_sched_subset = df_sched.iloc[:, [0, 12, 13, 29, 31, 33]].copy()
            df_sched_subset.columns = ['Fixture', 'val_M', 'val_N', 'val_AD', 'val_AF', 'val_AH']
            df_sched_subset.drop_duplicates(subset=['Fixture'], inplace=True)
            
            df_mls = df_mls.merge(df_sched_subset, on='Fixture', how='left')

            # --- Financial Rates ---
            cond_apple = df_mls['channel'].astype(str).str.strip().isin(['Apple TV+ US (www)', 'Apple TV+ (www)'])
            cond_usa_mls = (df_mls['programme'].astype(str).str.strip() == 'MLS Live') & (df_mls['channel country'].astype(str).str.strip().str.upper() == 'USA')
            cond_can_mls = (df_mls['programme'].astype(str).str.strip() == 'MLS Live') & (df_mls['channel country'].astype(str).str.strip().str.upper() == 'CANADA')

            val_ad = pd.to_numeric(df_mls['val_AD'], errors='coerce').fillna(0)
            val_af = pd.to_numeric(df_mls['val_AF'], errors='coerce').fillna(0)
            val_ah = pd.to_numeric(df_mls['val_AH'], errors='coerce').fillna(0)

            df_mls['1sec Nielsen Rate in EUR'] = np.select(
                [cond_apple, cond_usa_mls, cond_can_mls],
                [val_ad / 1.31, val_af / 1.31, val_ah / 1.31],
                default=0.0
            ).round(2)

            # --- US and CAN National Checks (Searching the raw files directly) ---
            val_m_blank = df_mls['val_M'].isna() | (df_mls['val_M'].astype(str).str.strip() == "")
            val_n_blank = df_mls['val_N'].isna() | (df_mls['val_N'].astype(str).str.strip() == "")
            
            is_in_usa = df_mls['Fixture'].astype(str).str.strip().isin(usa_fixtures)
            is_in_can = df_mls['Fixture'].astype(str).str.strip().isin(can_fixtures)

            df_mls['US National Check'] = np.select([val_m_blank, is_in_usa], ["OKAY", True], default=False)
            df_mls['CAN Check'] = np.select([val_n_blank, is_in_can], ["OKAY", True], default=False)

            df_mls['All Feeds Ready?'] = np.where((df_mls['US National Check'] != False) & (df_mls['CAN Check'] != False), "Yes", "No")

            # --- QC Logic ---
            df_mls['is_apple'] = df_mls['channel'].astype(str).str.contains('Apple TV', case=False, na=False)
            fixture_stats = df_mls.groupby('Fixture').agg(apple_cnt=('is_apple', 'sum'), total_cnt=('is_apple', 'count')).reset_index()
            df_mls = df_mls.merge(fixture_stats, on='Fixture', how='left')
            
            has_apple = df_mls['apple_cnt'] > 0
            has_linear = (df_mls['total_cnt'] - df_mls['apple_cnt']) > 0
            
            missing_stream = ~has_apple
            sched_mn_val = df_mls['val_M'].fillna('').astype(str).str.replace('nan', '').str.strip() + df_mls['val_N'].fillna('').astype(str).str.replace('nan', '').str.strip()
            missing_linear = (~has_linear) & (sched_mn_val != "")

            df_mls['QC'] = np.select(
                [missing_stream & missing_linear, missing_stream, missing_linear], 
                ["Missing Stream + Missing Linear", "Missing Stream", "Missing Linear"], 
                default=""
            )

            # --- Simulcasts ---
            multi_keys = set(df_multi.iloc[:, 0].astype(str).str.strip()) if not df_multi.empty else set()
            df_mls['Simulcasts'] = np.where(df_mls['QC'] != "", np.where(df_mls['Fixture'].astype(str).str.strip().isin(multi_keys), "Added", "Still Missing"), "")

        except IndexError:
            yield "data: [WARNING] Schedule tab doesn't have enough columns for mappings.\n\n"

    # --- Final Data Adjustments & Formatting ---
    df_mls['Audiences (000)'] = pd.to_numeric(df_mls['Audiences (000)'], errors='coerce').fillna(0.0)
    
    # Format to exactly 3 decimal places (except 0)
    df_mls['Audiences (000)'] = df_mls['Audiences (000)'].apply(lambda x: f"{x:.3f}" if x != 0.0 else 0)
    
    apple_tv_mask = df_mls['channel'].astype(str).str.contains('Apple TV', case=False, na=False)
    df_mls.loc[apple_tv_mask, 'Audiences (000)'] = "Streaming Channel"

    output = io.BytesIO()
    
    cols_to_drop = ['_calc_serial', '_join_chan', '_original_idx', 'val_M', 'val_N', 'val_AD', 'val_AF', 'val_AH', 'is_apple', 'apple_cnt', 'total_cnt']
    df_mls.drop(columns=cols_to_drop, inplace=True, errors='ignore')

    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_mls.to_excel(writer, sheet_name='Calculated Rates Export', index=False)
    
    output.seek(0)
    file_bytes = output.read()
    output.close()
    base64_file = base64.b64encode(file_bytes).decode('utf-8')
    del file_bytes
    del df_mls
    gc.collect()

    duration = round(time.time() - start_time, 2)
    yield f"data: [COMPLETED] Success! Audit took {duration}s.\n\n"
    yield f"file: {base64_file}\n\n"

    time.sleep(1)
    for p in [mls_p, usa_p, can_p]:
        try:
            if p and os.path.exists(p): os.remove(p)
        except: pass