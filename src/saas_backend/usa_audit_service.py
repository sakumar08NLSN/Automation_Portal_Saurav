import os
import time
import shutil
import pandas as pd
import numpy as np
import io
import base64
import gc
import re
from datetime import datetime

# --- CHANNEL NAME MAPPING ---
RAW_CHANNEL_MAPPING = {
    "American Heroes Channel": "American Heroes Channel", "Animal Planet": "Animal Planet",
    "Discovery en Espanol": "Discovery en Espanol", "FYI": "FYI", "HLN": "HLN",
    "Investigation Discovery": "Investigation Discovery", "Discovery Turbo": "Discovery Turbo",
    "Nat Geo Wild": "Nat Geo Wild", "National Geographic": "National Geographic",
    "OWN": "OWN", "Oxygen": "Oxygen", "Science": "Science", "TLC": "TLC",
    "TV One": "TV One", "Vice TV": "Vice TV", "National Geographic Mundo": "National Geographic Mundo",
    "Smithsonian Channel": "Smithsonian Channel", "Story Television": "Story Television",
    "Discovery Life Channel": "Discovery Life Channel", "The Weather Channel": "The Weather Channel",
    "Fox News": "Fox News", "NewsNation": "NewsNation", "Newsmax TV": "Newsmax TV",
    "Court TV": "Court TV", "MSNBC": "MSNBC", "CNN Espanol": "CNN Espanol",
    "Comedy.TV": "Comedy.TV", "beIN Sports USA": "beIN Sports USA",
    "FOX Sports 1": "Fox Sports 1 USA", "ESPNU": "ESPN USA", 
    "FOX Sports 2": "Fox Sports 2 USA", "GSN": "GSN", "E": "E",
    "Great American Family": "Great American Family", "Hallmark Mystery": "Hallmark Mystery",
    "MTV": "MTV", "MTV2": "MTV2", "Ovation": "Ovation", "SUNDANCE TV": "SUNDANCE TV",
    "TBS USA": "TBS USA", "Adult Swim": "Adult Swim", "Comedy Central": "Comedy Central",
    "FXX": "FXX", "MeTV Toons": "MeTV Toons", "Antenna TV": "Antenna TV",
    "Black Entertainment TV": "Black Entertainment TV", "Catchy Comedy": "Catchy Comedy",
    "Cleo TV": "Cleo TV", "CoziTV": "CoziTV", "DABL": "DABL", "Galavision": "Galavision",
    "IFC": "IFC", "Me TV": "Me TV", "Nick-at-Nite": "Nick-at-Nite", "TheGrio TV": "TheGrio TV",
    "TV Land": "TV Land", "Baby First TV": "Baby First TV", "Boomerang": "Boomerang",
    "Disney Channel": "Disney Channel", "Disney XD": "Disney XD", "Nick Jr.": "Nick Jr.",
    "CHARGE": "CHARGE", "Comet TV": "Comet TV", "Hallmark Family": "Hallmark Family",
    "Ion Television": "Ion Television", "Ion Mystery": "Ion Mystery", "Ion Plus": "Ion Plus",
    "Pop TV": "Pop TV", "Reelz": "Reelz", "Start TV": "Start TV", "UP": "UP",
    "USA Network": "USA Network", "WETV": "WETV", "Discovery Channel USA": "Discovery Channel USA",
    "Justice Central": "Justice Central", "ESPN 2 USA": "ESPN 2 USA", "NBA TV": "NBA TV",
    "BTN": "BTN", "TUDN USA": "TUDN USA", "Telemundo": "Telemundo", "ESPN Deportes": "ESPN Deportes",
    "Fox Deportes": "Fox Deportes", "Univision": "Univision", "CNN USA": "CNN USA",
    "CNBC USA": "CNBC USA", "Cooking Channel": "Cooking Channel", "Food Network Star": "Food Network Star",
    "Discovery Familia": "Discovery Familia", "Discovery Family": "Discovery Family",
    "HGTV USA": "HGTV USA", "DIY Network": "DIY Network", "Destination America": "Destination America",
    "Hogar de HGTV": "Hogar de HGTV", "RFD TV": "RFD TV", "Travel Channel": "Travel Channel",
    "Estrella TV": "Estrella TV", "Logo": "Logo", "GetTV": "GetTV", "TBD": "TBD",
    "Heroes + Icons": "Heroes + Icons", "INSP": "INSP", "Hallmark Channel": "Hallmark Channel",
    "Lifetime Movie Network": "Lifetime Movie Network", "Lifetime": "Lifetime",
    "Starz Primary": "Starz Primary", "A+E Network": "A+E Network", "History": "History",
    "Disney Junior": "Disney Junior", "Family ENT TV": "Family ENT TV", "Nicktoons": "Nicktoons",
    "Telexitos": "Telexitos", "Turner Network Television": "Turner Network Television",
    "TeenNick": "TeenNick", "NBC Universo": "NBC Universo", "The Cowboy Channel": "The Cowboy Channel",
    "The Golf Channel USA": "The Golf Channel USA", "Tennis Channel": "Tennis Channel",
    "Bounce TV": "Bounce TV", "Grit": "Grit", "FX Movie Channel": "FX Movie Channel",
    "TruTV": "TruTV", "Showtime Prime": "Showtime Prime", "Bet Her": "Bet Her",
    "Bravo": "Bravo", "NFL Network": "NFL Network", "Paramount Network": "Paramount Network",
    "beIN Sports Espanol USA": "beIN Sports Espanol USA", "VH1": "VH1", "LAFF": "LAFF",
    "Syfy": "Syfy", "UniMas": "UniMas", "BBC America": "BBC America", "NBC True CRMZ": "NBC True CRMZ",
    "ESPN USA": "ESPN USA", "AMC": "AMC", "FX": "FX", "MLB Network": "MLB Network",
    "CMT": "CMT", "HBO Prime": "HBO Prime", "CBS": "CBS", "NBC": "NBC", "ABC": "ABC",
    "Fox Business Network": "Fox Business Network", "Tlnovelas": "Tlnovelas",
    "Freeform": "Freeform", "Cartoon Network": "Cartoon Network", "Nickelodeon": "Nickelodeon",
    "CW": "CW", "FOX USA": "FOX USA", "MotorTrend": "MotorTrend", "GalaNovelas": "GalaNovelas",
    "FS1": "Fox Sports 1 USA", "FS2": "Fox Sports 2 USA", "FOX BUSINESS": "Fox Business Network",
    "DISCOVERY CHANNEL": "Discovery Channel USA", "CNBC": "CNBC USA", "USA": "USA Network",
    "ESPN2": "ESPN 2 USA", "FOX (WNYW) New York": "FOX USA"
}
CHANNEL_MAPPING = {k.strip().upper(): v.strip().upper() for k, v in RAW_CHANNEL_MAPPING.items()}
def normalize_channel_name(name):
    if pd.isna(name): return "UNKNOWN"
    n = str(name).strip().upper()
    if any(x in n for x in ["WNYW", "WFXT", "FOX USA"]) or (n.startswith("FOX") and "(" in n):
        return "FOX USA"
    if any(x in n for x in ["KTLA", "KDAF", "CW"]) or (n.startswith("CW") and "(" in n):
        return "CW"
    if "FOX SPORTS 1" in n or "FS1" in n: return "FOX SPORTS 1 USA"
    if "FOX SPORTS 2" in n or "FS2" in n: return "FOX SPORTS 2 USA"
    if "ESPN 2" in n or "ESPN2" in n: return "ESPN 2 USA"
    if "ESPN" in n: return "ESPN USA"
    if "BTN" in n: return "BTN"
    if "NBC" in n: return "NBC"
    return n

def get_numeric_serial_vectorized(df, date_col, time_col):
    try:
        dt = pd.to_datetime(df[date_col], format='mixed', dayfirst=True, errors='coerce')
        tm_series = df[time_col].astype(str).str.strip()
        tm = pd.to_timedelta(tm_series, errors='coerce')
        if tm.isna().any():
            tm_dt = pd.to_datetime(tm_series, format='%H:%M:%S', errors='coerce')
            tm = pd.to_timedelta(tm_dt.dt.strftime('%H:%M:%S'))
        base_date = datetime(1899, 12, 30)
        return ((dt - base_date).dt.days + (tm.dt.total_seconds() / 86400.0)).fillna(0)
    except Exception:
        return pd.Series(0, index=df.index)

def clean_val(val):
    if pd.isna(val) or str(val).strip().upper() in ["#N/A", "#REF!", "NAN", "-", ""]:
        return 0.0
    try:
        return float(str(val).replace('$', '').replace(',', '').strip())
    except:
        return 0.0

def format_time_string(val):
    t = str(val).strip()
    return t[:5] if len(t) >= 5 else t

async def process_usa_audit_logic_stream(usa_data, export_file, cpm_file, upload_folder):
    timestamp = int(time.time())
    work_dir = upload_folder if os.name == 'nt' else "/tmp"
    
    yield "data: [LOG] USA Engine Active. Initializing Transparency Audit...\n\n"
    usa_p, exp_p, cpm_p = [os.path.join(work_dir, f"{x}_{timestamp}.xlsx") for x in ['u','e','c']]

    try:
        for f_obj, p in [(usa_data, usa_p), (export_file, exp_p), (cpm_file, cpm_p)]:
            with open(p, "wb") as f: shutil.copyfileobj(f_obj.file, f)

        xl_usa = pd.ExcelFile(usa_p, engine='calamine')
        df_usa_raw = pd.read_excel(xl_usa, sheet_name=0, skiprows=5)
        xl_usa.close()

        aud_col = next((c for c in df_usa_raw.columns if "Aud Metered" in str(c) and "14+" not in str(c)), None)
        if not aud_col: aud_col = next((c for c in df_usa_raw.columns if "Estimates" in str(c)), df_usa_raw.columns[-1])

        usa_lookup = pd.DataFrame({
            'u_start': get_numeric_serial_vectorized(df_usa_raw, 'Date', 'Start'),
            'u_end': get_numeric_serial_vectorized(df_usa_raw, 'Date', 'End'),
            '_join_chan': df_usa_raw['TV-Channel'].apply(normalize_channel_name),
            'rating_aud': df_usa_raw[aud_col],
            'rating_prog': df_usa_raw['Program Title'],
            'str_start': df_usa_raw['Start'].apply(format_time_string),
            'str_end': df_usa_raw['End'].apply(format_time_string)
        }).dropna(subset=['u_start'])
        
        usa_lookup.loc[usa_lookup['u_end'] < usa_lookup['u_start'], 'u_end'] += 1.0
        usa_grouped = {chan: group for chan, group in usa_lookup.groupby('_join_chan')}

        xl_cpm = pd.ExcelFile(cpm_p, engine='calamine')
        cpm_sheet = next((s for s in xl_cpm.sheet_names if "cpm" in s.lower()), xl_cpm.sheet_names[0])
        df_cpm = pd.read_excel(xl_cpm, sheet_name=cpm_sheet, skiprows=2)
        cpm_map = {normalize_channel_name(row.iloc[0]): clean_val(row.iloc[2]) for _, row in df_cpm.iterrows()}
        xl_cpm.close()

        xl_exp = pd.ExcelFile(exp_p, engine='calamine')
        df_export = pd.read_excel(xl_exp, skiprows=3)
        xl_exp.close()

        date_col = next((c for c in df_export.columns if 'start (date)' in str(c).lower()), df_export.columns[5])
        time_col = next((c for c in df_export.columns if 'start (time)' in str(c).lower()), df_export.columns[6])
        dur_col = next((c for c in df_export.columns if 'duration' in str(c).lower()), df_export.columns[7])
        chan_col = next((c for c in df_export.columns if 'channel' in str(c).lower() and 'country' not in str(c).lower()), df_export.columns[2])

        df_export['_original_idx'] = df_export.index
        df_export['e_start'] = get_numeric_serial_vectorized(df_export, date_col, time_col)
        tm_dur = pd.to_timedelta(df_export[dur_col].astype(str), errors='coerce')
        df_export['e_end'] = df_export['e_start'] + (tm_dur.dt.total_seconds() / 86400.0).fillna(0)
        df_export['_join_chan'] = df_export[chan_col].apply(normalize_channel_name)

        def find_best_rating(row):
            chan = row['_join_chan']
            default_out = [0.0, "#N/A", "", "", "", "", "", ""]
            if chan not in usa_grouped: return pd.Series(default_out)
            
            cands = usa_grouped[chan]
            e_s, e_e = row['e_start'], row['e_end']
            
            cands = cands[(cands['u_start'] < e_e) & (cands['u_end'] > e_s)]
            if cands.empty: return pd.Series(default_out)
            
            export_text = (str(row.get('event', '')) + " " + str(row.get('matchday', ''))).upper()
            export_keywords = set(re.findall(r'\b\w{3,}\b', export_text))
            
            best_score = -999999
            best_row = None
            cand_list = []
            final_reason = ""
            
            for _, c in cands.iterrows():
                prog_name = str(c['rating_prog']).upper()
                usa_keywords = set(re.findall(r'\b\w{3,}\b', prog_name))
                overlap_sec = max(0, (min(e_e, c['u_end']) - max(e_s, c['u_start'])) * 86400.0)
                kw_match_count = len(export_keywords.intersection(usa_keywords))
                
                score = (overlap_sec / 60.0) * 10 
                score += (kw_match_count * 5000)   
                score -= abs(c['u_start'] - e_s) * 500
                
                cand_str = f"{c['str_start']} to {c['str_end']} - {c['rating_prog']} (Aud: {clean_val(c['rating_aud'])})"
                cand_list.append(cand_str)
                
                if score > best_score:
                    best_score = score
                    best_row = c
                    final_reason = f"Matched via {kw_match_count} keywords and {int(overlap_sec/60)} mins overlap."
            
            c_cols = (cand_list + [""] * 4)[:4]
            if best_row is not None:
                sel_str = f"{best_row['str_start']} to {best_row['str_end']} - {best_row['rating_prog']}"
                return pd.Series([clean_val(best_row['rating_aud']), best_row['rating_prog'], 
                                 c_cols[0], c_cols[1], c_cols[2], c_cols[3], sel_str, final_reason])
            return pd.Series(default_out)

        df_export[['_val_aud', '_val_prog', 'Candidate 1', 'Candidate 2', 'Candidate 3', 'Candidate 4', 'Selected Match Details', '_match_logic']] = df_export.apply(find_best_rating, axis=1)

        def finalize(row):
            aud = row['_val_aud']
            cpm = clean_val(cpm_map.get(row['_join_chan'], 0))
            rate = (aud * cpm) / (30 * 1.31)
            
            logic_expl = (f"Chosen USA program '{row['Program check']}' matches the export window. "
                          f"Logic: {row['_match_logic']} Rate calculated as: "
                          f"({aud} Aud * {cpm} CPM) / (30s * 1.31 Exch) = {round(rate, 3)} EUR.")
            
            return pd.Series([aud, round(rate, 3), row['_val_prog'], "No", cpm, logic_expl])

        df_export[["aud_all_esti (000's)", "1sec Nielsen Rate in EUR", "Program check", "Internal Overlap", "Applied CPM", "Logic Explanation"]] = df_export.apply(finalize, axis=1)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            cols_to_drop = ['_original_idx', 'e_start', 'e_end', '_join_chan', '_val_aud', '_val_prog', '_match_logic']
            df_export.sort_values('_original_idx').drop(columns=cols_to_drop, errors='ignore').to_excel(writer, sheet_name='Calculated Export', index=False)
        
        output.seek(0)
        yield "data: [COMPLETED] Success! Audit logs and CPM column added.\n\n"
        yield f"file: {base64.b64encode(output.read()).decode('utf-8')}\n\n"
    except Exception as e:
        yield f"data: [ERROR] {str(e)}\n\n"
    finally:
        for p in [usa_p, exp_p, cpm_p]:
            if os.path.exists(p): os.remove(p)
        gc.collect()
        
# import os
# import time
# import shutil
# import pandas as pd
# from datetime import datetime

# # --- 1. VISUAL KEY HELPER ---
# def get_excel_serial_stitching(dt_val, tm_val):
#     """Creates the string 'NBC460250.625' for Excel display."""
#     try:
#         dt = pd.to_datetime(dt_val)
#         tm = pd.to_datetime(str(tm_val))
#         base_date = datetime(1899, 12, 30)
#         date_int = (dt - base_date).days
#         time_dec = (tm.hour * 3600 + tm.minute * 60 + tm.second) / 86400.0
        
#         full_str = f"{time_dec:.15f}"
#         integer_part, decimal_part = full_str.split('.')
#         truncated_decimal = decimal_part[:9]
        
#         stitched = f"{date_int}{integer_part}.{truncated_decimal}"
#         return stitched.rstrip('0').rstrip('.')
#     except:
#         return "0"

# # --- 2. LOGIC KEY HELPER ---
# def get_numeric_serial(dt_val, tm_val):
#     """Calculates float for sorting/matching."""
#     try:
#         dt = pd.to_datetime(dt_val)
#         tm = pd.to_datetime(str(tm_val))
#         base_date = datetime(1899, 12, 30)
#         date_int = (dt - base_date).days
#         time_dec = (tm.hour * 3600 + tm.minute * 60 + tm.second) / 86400.0
#         return float(date_int + time_dec)
#     except:
#         return None # Return None instead of 0.0 to easily identify bad rows

# def clean_val(val):
#     if pd.isna(val) or str(val).strip().upper() in ["#N/A", "#REF!", "NAN", "-", ""]:
#         return 0.0
#     s_val = str(val).replace('$', '').replace(',', '').strip()
#     try: return float(s_val)
#     except: return 0.0

# def process_usa_audit_logic(usa_data, export_file, cpm_file, upload_folder, output_folder):
#     timestamp = int(time.time())
#     print(f"\n--- [LOG] Process Started at {timestamp} ---")
    
#     usa_p = os.path.join(upload_folder, f"u_{timestamp}.xlsx")
#     exp_p = os.path.join(upload_folder, f"e_{timestamp}.xlsx")
#     cpm_p = os.path.join(upload_folder, f"c_{timestamp}.xlsx")

#     for f_obj, p in [(usa_data, usa_p), (export_file, exp_p), (cpm_file, cpm_p)]:
#         with open(p, "wb") as f:
#             shutil.copyfileobj(f_obj.file, f)

#     # --- LOAD USA DATA ---
#     xl_usa = pd.ExcelFile(usa_p)
#     target_sheet = next((s for s in xl_usa.sheet_names if "usadata" in s.lower() or "sheet1" in s.lower()), xl_usa.sheet_names[0])
#     df_usa = pd.read_excel(usa_p, sheet_name=target_sheet, skiprows=5)
    
#     IDX_CHAN = 4; IDX_DATE = 8; IDX_START = 12; IDX_PROG = 17; IDX_AUD = 30 

#     # Prepare USA Lookup
#     usa_lookup = pd.DataFrame()
#     usa_lookup['_calc_serial'] = df_usa.apply(lambda r: get_numeric_serial(r.iloc[IDX_DATE], r.iloc[IDX_START]), axis=1)
#     usa_lookup['_join_chan'] = df_usa.iloc[:, IDX_CHAN].astype(str).str.strip().str.upper()
#     usa_lookup['_val_aud'] = df_usa.iloc[:, IDX_AUD]
#     usa_lookup['_val_prog'] = df_usa.iloc[:, IDX_PROG]
    
#     # --- CRITICAL FIX: CLEAN NULLS BEFORE MERGE ---
#     initial_len = len(usa_lookup)
    
#     # 1. Drop rows where channel is 'NAN' or empty string (often caused by empty excel rows)
#     usa_lookup = usa_lookup[usa_lookup['_join_chan'].replace('NAN', '') != '']
    
#     # 2. Drop rows where serial calculation failed (returned None)
#     usa_lookup = usa_lookup.dropna(subset=['_calc_serial'])
    
#     print(f"[LOG] Cleaning USA Data: Dropped {initial_len - len(usa_lookup)} empty/invalid rows.")
    
#     usa_lookup = usa_lookup.sort_values('_calc_serial')

#     # Prepare Visual Reference Tab
#     df_usa['cont date time'] = df_usa.apply(lambda r: get_excel_serial_stitching(r.iloc[IDX_DATE], r.iloc[IDX_START]), axis=1)
#     df_usa['concat channel date time'] = df_usa.iloc[:, IDX_CHAN].astype(str).str.strip() + df_usa['cont date time']

#     # --- LOAD AUX SHEETS ---
#     yt_sheet = next((s for s in xl_usa.sheet_names if "youtube" in s.lower()), None)
#     t3_sheet = next((s for s in xl_usa.sheet_names if "table3" in s.lower()), None)
#     df_yt = pd.read_excel(usa_p, sheet_name=yt_sheet) if yt_sheet else pd.DataFrame()
#     df_t3 = pd.read_excel(usa_p, sheet_name=t3_sheet) if t3_sheet else pd.DataFrame()

#     # --- LOAD EXPORT & CPM ---
#     df_export = pd.read_excel(exp_p, skiprows=3)
    
#     # Load CPM (Headers on Row 3 -> skiprows=2)
#     df_cpm = pd.read_excel(cpm_p, skiprows=2)
#     df_cpm.rename(columns={df_cpm.columns[0]: 'DMA'}, inplace=True)
#     df_cpm['DMA'] = df_cpm['DMA'].astype(str).str.strip().str.upper()

#     # Prepare Export for Merge
#     df_export['_calc_serial'] = df_export.apply(lambda r: get_numeric_serial(r['progr. start (date)'], r['progr. start (time)']), axis=1)
#     df_export['_join_chan'] = df_export['channel'].astype(str).str.strip().str.upper()
#     df_export = df_export.sort_values('_calc_serial')

#     # --- MERGE (Get Audience) ---
#     print("[LOG] Running Approximate Time Match...")
#     merged = pd.merge_asof(
#         df_export, usa_lookup,
#         on='_calc_serial', by='_join_chan', direction='backward', suffixes=('', '_lookup')
#     )

#     # --- CALCULATE RATES ---
#     target_demo = f"{datetime.now().month}P2+"
#     print(f"[LOG] Target CPM Column: '{target_demo}'")

#     def finalize_row(row):
#         # 1. Visual Key
#         chan_raw = str(row['channel']).strip()
#         display_serial = get_excel_serial_stitching(row['progr. start (date)'], row['progr. start (time)'])
#         v5_key = f"{chan_raw}{display_serial}"
        
#         # 2. Audience
#         aud = clean_val(row['_val_aud'])
#         prog = row['_val_prog'] if pd.notna(row['_val_prog']) else "#N/A"
        
#         # 3. Logic Setup
#         chan_clean = chan_raw.lower()
#         chan_upper = chan_raw.upper()
#         matchday = str(row.get('matchday', '')).strip().lower()

#         # --- AUDIENCE OVERRIDE (YouTube) ---
#         if "youtube" in chan_clean and not df_yt.empty:
#             match = df_yt[df_yt.iloc[:, 12].astype(str).str.strip().str.lower() == matchday]
#             if not match.empty:
#                 aud = clean_val(match.iloc[0, 16])
#                 prog = "YouTube Match"
#             else:
#                 aud = 0.0

#         # --- RATE CALCULATION ---
#         rate = 0.0
        
#         # A. YouTube
#         if "youtube" in chan_clean and not df_yt.empty:
#             match = df_yt[df_yt.iloc[:, 0].astype(str).str.strip().str.lower() == matchday]
#             rate = clean_val(match.iloc[0, 19]) if not match.empty else 0.0

#         # B. Peacock
#         elif "peacock" in chan_clean and not df_t3.empty:
#             match = df_t3[df_t3.iloc[:, 0].astype(str).str.strip().str.lower() == matchday]
#             rate = clean_val(match.iloc[0, 2]) if not match.empty else 0.0

#         # C. Standard CPM (NBC, Fox, etc.)
#         else:
#             if chan_upper in df_cpm['DMA'].values:
#                 if target_demo in df_cpm.columns:
#                     cpm_raw = df_cpm.loc[df_cpm['DMA'] == chan_upper, target_demo].values[0]
#                     cpm_val = clean_val(cpm_raw)
#                     rate = (aud * cpm_val) / 30 / 1.31
#                 else:
#                     rate = 0.0 # Column missing
#             else:
#                 rate = 0.0

#         return pd.Series([aud, rate, v5_key, prog])

#     merged[["aud_all_esti (000's)", "1sec Nielsen Rate in EUR", "Concat Channel Date Time", "Program check"]] = merged.apply(finalize_row, axis=1)

#     # Cleanup
#     final_order = [
#         "gID", "channel country", "channel", "programme", "programme category",
#         "progr. start (date)", "progr. start (time)", "progr. duration", "progr. end (time)",
#         "sports", "event", "matchday", "home team", "away team", "rating source",
#         "rate/rating country", "aud_all_orig", "official Share All Individuals (in %)",
#         "aud_all_esti (000's)", "1sec Repucom Rate in EUR", "1sec Nielsen Rate in EUR",
#         "Concat Channel Date Time", "Program check"
#     ]
#     merged = merged[[c for c in final_order if c in merged.columns]]

#     out_filename = f"USA_Audit_Calculated_{timestamp}.xlsx"
#     out_path = os.path.join(output_folder, out_filename)
    
#     with pd.ExcelWriter(out_path, engine='openpyxl') as writer:
#         merged.to_excel(writer, sheet_name='Calculated Export', index=False)
#         df_usa.to_excel(writer, sheet_name='USA Data Reference', index=False)
        
#     print(f"[LOG] Process Complete. File saved: {out_filename}")
#     return out_path, out_filename