import React, { useState, useEffect } from "react";
import { Upload, X, CheckCircle, AlertTriangle, FileText, Loader, Download } from "lucide-react";
// import { DataGrid, GridColDef, GridRowId } from "@mui/x-data-grid";
import { useAppSelector } from "@/app/redux"; 
import { dataGridClassNames, dataGridSxStyles } from "@/lib/utils"; 
// 💡 IMPORT THE NEW RTK QUERY HOOK AND INTERFACE
import { useRunQcChecksMutation, QcSummaryResult } from "@/state/api"; 
import { DataGrid, GridColDef } from "@mui/x-data-grid";


export interface QcRunResponse {
    status: string;
    message: string;
    download_url: string;
    summaries: QcSummaryResult[];
}

const getSummaryColumns = (isDarkMode: boolean): GridColDef[] => [
  { field: 'description', headerName: 'Description', flex: 1.5, minWidth: 250, sortable: false },
  { field: 'action', headerName: 'Action Type', width: 120, sortable: false },
  { 
    field: 'status', headerName: 'Status', width: 120,
    // Add custom rendering for Status if desired, similar to your old code:
    renderCell: (params) => {
        const status = params.value as string;
        const isSuccess = status === 'Completed' || status === 'Passed';
        const color = isSuccess ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800';
        return (<span className={`inline-flex rounded-full px-2 text-xs font-semibold leading-5 ${color}`}>{status}</span>);
    }
  },
  { field: 'total_issues_flagged', headerName: 'Flag Count', width: 100 },
  { field: 'id', headerName: 'ID', width: 50 },
];

// --- CONFIGURATION ---
// The base URL is now handled by RTK Query's setup in api.ts

// --- MOCK DATA FOR AVAILABLE CHECKS (No change) ---
const availableChecks = [
  { key: "period_check", name: "Period Integrity Check", type: "Audit" },
  { key: "completeness_check", name: "Field Completeness Check", type: "Audit" },
  { key: "overlap_duplicate_daybreak_check", name: "Overlap & Duplication Check", type: "Audit" },
  { key: "program_category_check", name: "Program Category Consistency", type: "Audit" },
  { key: "duration_check", name: "Start/End Duration Integrity", type: "Audit" },
  { key: "rates_and_ratings_check", name: "Rates and Ratings Consistency", type: "Audit" },
  { key: "duplicated_markets_check", name: "Market Duplicated Markets Cross-Check", type: "Audit" },
  { key: "country_channel_id_check", name: "Country/Channel ID Consistency", type: "Audit" },
  { key: "client_lstv_ott_check", name: "Client/LSTV/OTT Source Check", type: "Audit" },
  { key: "check_event_matchday_competition", name: "Event Matchday Consistency", type: "Audit" },
];

type BoardViewProps = {
  id: string;
  setIsModalNewTaskOpen: (isOpen: boolean) => void;
};


const BoardView = ({ id, setIsModalNewTaskOpen }: BoardViewProps) => {
  // 💡 RTK QUERY: Initialize the mutation hook
  const [runQc, { 
    isLoading, 
    isSuccess, 
    isError, 
    error, 
    data: summaryData 
}] = useRunQcChecksMutation();


  // --- FILE STATE ---
  const [selectedBSRFile, setSelectedBSRFile] = useState<File | null>(null);
  const [selectedRoscoFile, setSelectedRoscoFile] = useState<File | null>(null);
  const [selectedDataFile, setSelectedDataFile] = useState<File | null>(null); 
  const [selectedMacroFile, setSelectedMacroFile] = useState<File | null>(null); 

  // --- PROCESSING & UI STATE ---
  const [selectedChecks, setSelectedChecks] = useState<string[]>([]);
  // ❌ DEPRECATED: Retaining this but it will be null/unused in the new logic
  const [qcResultBlob, setQcResultBlob] = useState<{data: Blob, name: string} | null>(null); 
  
  const [processStatus, setProcessStatus] = useState<'idle' | 'complete' | 'error'>('idle');
  const [localError, setLocalError] = useState<string | null>(null);
  // ✅ NEW: Stores the download URL and Filename from the JSON response
  const [qcResultMeta, setQcResultMeta] = useState<{url: string, name: string} | null>(null);

  const isDarkMode = useAppSelector((state) => state.global.isDarkMode);
  const columnVisibilityModel = { check_key: false, };

  const isReadyToRun = selectedBSRFile && selectedRoscoFile && selectedChecks.length > 0;
  const isProcessingComplete = processStatus === 'complete';

  // 💡 COMBINED STATUS
  const combinedStatus = isLoading ? 'loading' : isProcessingComplete ? 'complete' : localError ? 'error' : 'idle';
  
  // --- MOCK SUMMARY DATA (used for table if real data is absent) ---
  const mockSummary: QcSummaryResult[] = [
    { id: 1, description: "Period Integrity Check", action: "Audit", status: "Completed", total_issues_flagged: 0 }, 
    { id: 2, description: "Field Completeness Check", action: "Audit", status: "Issue Found", total_issues_flagged: 15 },
    { id: 3, description: "Rates and Ratings Consistency", action: "Audit", status: "Issue Found", total_issues_flagged: 7098 },
    { id: 4, description: "Duplicated Markets Cross-Check", action: "Audit", status: "Issue Found", total_issues_flagged: 607 },
    { id: 5, description: "Duration Limits Check", action: "Audit", status: "Passed", total_issues_flagged: 0 },
  ];

  // --- EFFECT TO HANDLE RTK QUERY RESPONSE (Success and Error) ---
  useEffect(() => {
    if (isSuccess && summaryData) {
      // 1. CAST RESPONSE
      const response = summaryData as unknown as QcRunResponse;

      // 2. UPDATE STATUS & ERROR
      setProcessStatus('complete');
      setLocalError(null);
      
      // 3. SET DOWNLOAD METADATA
      // The output_file is typically included in the download_url query param
      const urlParams = new URLSearchParams(response.download_url.split('?')[1]);
      const filename = urlParams.get('filename') || "QC_Result.xlsx";

      setQcResultMeta({
         url: response.download_url, // e.g., /api/download_file?filename=...
         name: filename
      });
      
      // 4. NOTE: We assume the DataGrid will use summaryData.summaries directly.

    } else if (isError) {
      // 1. UPDATE STATUS & ERROR
      setProcessStatus('error');
      // Use the RTK Query error payload for detailed messages
      setLocalError(`❌ API Error: ${(error as any).data?.detail || 'Processing failed. Check console/network logs.'}`);
      setQcResultMeta(null);
    }
  }, [isSuccess, isError, summaryData, error]);
    
  
  // --- 1. RTK QUERY TRIGGER LOGIC ---
  const handleRunChecks = async () => {
    if (!isReadyToRun || isLoading) return;
    
    setProcessStatus('idle'); 
    setLocalError(null);
    setQcResultMeta(null); // Clear previous results

    const formData = new FormData();
    formData.append('rosco_file', selectedRoscoFile as File);
    formData.append('bsr_file', selectedBSRFile as File);
    if (selectedDataFile) { formData.append('data_file', selectedDataFile); }
    if (selectedMacroFile) { formData.append('macro_file', selectedMacroFile); }
    formData.append('selected_checks', JSON.stringify(selectedChecks));

    try {
      await runQc(formData).unwrap();
    } catch (err) {
      console.error("QC Check execution failed:", err);
    }
  };

  // --- 2. DOWNLOAD HANDLER (Uses the URL Metadata) ---
  const handleDownload = () => {
    if (!qcResultMeta) return;

    // The backend URL is constructed using the BASE_URL and the relative URL provided by FastAPI
    // Note: process.env.NEXT_PUBLIC_API_BASE_URL should be set to something like http://localhost:8000/
    const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/';
    
    // We construct the full URL. new URL handles merging the base and relative path correctly.
    // Example: new URL('/api/download_file?filename=...', 'http://localhost:8000/').href
    const fullDownloadUrl = new URL(qcResultMeta.url, baseUrl).href;
    
    // Trigger the browser download
    window.location.href = fullDownloadUrl;
  };
  
  // --- 3. FILE CHANGE HANDLER (No change) ---
  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>, fileType: 'bsr' | 'rosco' | 'data' | 'macro') => {
    const file = event.target.files?.[0];
    if (fileType === 'bsr') {
      setSelectedBSRFile(file || null);
    } else if (fileType === 'rosco') {
      setSelectedRoscoFile(file || null);
    } else if (fileType === 'data') {
      setSelectedDataFile(file || null); 
    } else if (fileType === 'macro') {
      setSelectedMacroFile(file || null); 
    }
  };

  // --- 4. CHECKBOX TOGGLE HANDLER (No change) ---
  const handleCheckToggle = (key: string) => {
    setSelectedChecks(prev => 
      prev.includes(key) ? prev.filter(k => k !== key) : [...prev, key]
    );
  };

  return (
    <div className="grid grid-cols-1 gap-8 xl:grid-cols-4 w-full">
      
      {/* COLUMN 1: INPUTS (Takes 3/4 columns on XL screens) */}
      <div className="col-span-1 xl:col-span-4 rounded-lg bg-white p-6 shadow dark:bg-dark-secondary">
        
        {/* 💡 START: HORIZONTAL CONTAINER FOR CHECKLIST & UPLOADS */}
        {/* We use flex-col on small screens and switch to horizontal flex-row on medium/large screens */}
        <div className="flex flex-col md:flex-row md:space-x-6 space-y-6 md:space-y-0">
            
            {/* ---------------------------------------------------- */}
            {/* 💡 LEFT SIDE: CHECKLIST (Section 2) - Takes half the width (flex-1) */}
            {/* ---------------------------------------------------- */}
            <div className="flex-1 space-y-4 pt-0">
                <h3 className="text-xl font-bold dark:text-white">Select Checks</h3>
                {/* Fixed max-h-96 to create vertical space matching the uploads */}
                <div className="max-h-96 space-y-2 overflow-y-auto pr-2 border border-gray-200 dark:border-gray-700 rounded p-2">
                  {availableChecks.map((check) => (
                    <div key={check.key} className="flex items-center justify-between rounded-md p-3 hover:bg-gray-100 dark:hover:bg-gray-700">
                      <label className="flex items-center">
                        <input
                          type="checkbox"
                          checked={selectedChecks.includes(check.key)}
                          onChange={() => handleCheckToggle(check.key)}
                          className="form-checkbox h-4 w-4 text-blue-600 rounded"
                        />
                        <span className="ml-3 text-sm dark:text-gray-200">{check.name}</span>
                      </label>
                      <span className="text-xs text-blue-500 bg-blue-100 dark:bg-blue-900/50 dark:text-blue-300 px-2 py-0.5 rounded-full">
                        {check.type}
                      </span>
                    </div>
                  ))}
                </div>
            </div>

            {/* ---------------------------------------------------- */}
            {/* 💡 RIGHT SIDE: FILE UPLOADS (Section 1) - Takes half the width (flex-1) */}
            {/* ---------------------------------------------------- */}
            <div className="flex-1 space-y-4 pt-0">
                <h3 className="text-xl font-bold dark:text-white">QC File Selection</h3>
                
                {/* --- FIRST HORIZONTAL ROW (BSR and ROSCO) --- */}
                <div className="flex space-x-4">
                    {/* BSR File (Mandatory) */}
                    <div className="flex-1">
                        <p className="font-medium text-gray-700 dark:text-gray-300">BSR Data File (Mandatory)</p>
                        <label className="flex flex-col items-center justify-center border-2 border-dashed border-blue-300 p-4 cursor-pointer rounded-lg bg-blue-50 dark:bg-blue-950/50 h-full">
                            <FileText className="h-8 w-8 text-blue-600" />
                            <p className="mt-2 text-sm text-blue-600 dark:text-blue-300 text-center">{selectedBSRFile ? selectedBSRFile.name : "Upload BSR (.xlsx)"}</p>
                            <input type="file" className="hidden" accept=".xlsx" onChange={(e) => handleFileChange(e, 'bsr')} />
                        </label>
                    </div>

                    {/* ROSCO File (Mandatory) */}
                    <div className="flex-1">
                        <p className="font-medium text-gray-700 dark:text-gray-300">Rosco  File (Mandatory)</p>
                        <label className="flex flex-col items-center justify-center border-2 border-dashed border-green-300 p-4 cursor-pointer rounded-lg bg-green-50 dark:bg-green-950/50 h-full">
                            <FileText className="h-8 w-8 text-green-600" />
                            <p  className="mt-2 text-sm text-green-600 dark:text-green-300 text-center">{selectedRoscoFile ? selectedRoscoFile.name : "Upload Rosco (.xlsx)"}</p>
                            <input type="file" className="hidden" accept=".xlsx" onChange={(e) => handleFileChange(e, 'rosco')} />
                        </label>
                    </div>
                </div>

                {/* --- SECOND HORIZONTAL ROW (Data File and Macro File) --- */}
                <div className="flex space-x-4 pt-4"> 
                    {/* DATA File (Optional) */}
                    <div className="flex-1">
                        <p className="font-medium text-gray-700 dark:text-gray-300">Client Data File (Optional)</p>
                        <label className={`flex flex-col items-center justify-center p-4 cursor-pointer rounded-lg border-2 border-dashed h-full
                                            ${selectedDataFile ? 'border-yellow-500 bg-yellow-50 dark:bg-yellow-900/50' : 'border-gray-300 bg-gray-50 dark:bg-gray-800'}`}>
                            <FileText className={`h-8 w-8 ${selectedDataFile ? 'text-yellow-700' : 'text-gray-500'}`} />
                            <p className={`mt-2 text-sm text-center ${selectedDataFile ? 'text-yellow-700' : 'text-gray-500'} dark:text-gray-400`}>{selectedDataFile ? selectedDataFile.name : "Upload Client Data (.xlsx)"}</p>
                            <input type="file" className="hidden" accept=".xlsx" onChange={(e) => handleFileChange(e, 'data')} />
                        </label>
                    </div>

                    {/* MACRO File (Optional) */}
                    <div className="flex-1">
                        <p className="font-medium text-gray-700 dark:text-gray-300">Macro File (Optional)</p>
                        <label className={`flex flex-col items-center justify-center p-4 cursor-pointer rounded-lg border-2 border-dashed h-full
                                            ${selectedMacroFile ? 'border-purple-500 bg-purple-50 dark:bg-purple-900/50' : 'border-gray-300 bg-gray-50 dark:bg-gray-800'}`}>
                            <FileText className={`h-8 w-8 ${selectedMacroFile ? 'text-purple-700' : 'text-gray-500'}`} />
                            <p className={`mt-2 text-sm text-center ${selectedMacroFile ? 'text-purple-700' : 'text-gray-500'} dark:text-gray-400`}>{selectedMacroFile ? selectedMacroFile.name : "Upload Macro (.xlsm)"}</p>
                            <input type="file" className="hidden" accept=".xlsm" onChange={(e) => handleFileChange(e, 'macro')} />
                        </label>
                    </div>
                </div>
            </div>
        </div>
        {/* 💡 END: HORIZONTAL CONTAINER FOR CHECKLIST & UPLOADS */}

        
        {/* RUN BUTTON (Spans full width below the horizontal section) */}
        <button
          onClick={handleRunChecks}
          // The disabled check is correct: only disable if loading
          disabled={!isReadyToRun || combinedStatus === 'loading'}
          className="w-full flex items-center justify-center rounded-md bg-blue-500 px-4 py-2 text-white font-semibold hover:bg-blue-600 disabled:bg-gray-400 mt-4"
        >
          {combinedStatus === 'loading' ? (
            <>
              <Loader className="mr-2 h-5 w-5 animate-spin" />
              Running Checks...
            </>
          ) : combinedStatus === 'complete' ? ( // 💡 ADDED: Check for 'complete' state
            <>
              <CheckCircle className="mr-2 h-5 w-5" />
              Checks Successful!
            </>
          ) : (
            // This is the default 'idle' or 'error' state
            <>
              <FileText className="mr-2 h-5 w-5" />
              Run {selectedChecks.length} Checks
            </>
          )}
        </button>
        
        <div className="mt-4">
          {localError && (
            <div className="p-4 text-center bg-red-100 rounded-lg dark:bg-red-900/50 text-red-700 dark:text-red-200">
                <AlertTriangle className="inline h-5 w-5 mr-2" />
                {localError}
            </div>
          )}
        </div>
      </div>

      {/* 💡 FIX 3: RESULTS COLUMN now takes 1 column (25%) */}
      <div className="col-span-4 space-y-6">
        <h3 className="text-xl font-bold dark:text-white">3. Validation Results Summary</h3>
        
        {/* 🚨 FIX: Check against the correct state variable: qcResultMeta */}
        {combinedStatus === 'complete' && qcResultMeta && (
            <div className="p-4 bg-green-100 dark:bg-green-900/50 rounded-lg shadow border border-green-300">
                <p className="text-sm font-semibold text-green-800 dark:text-green-200 mb-2">
                    ✅ Processing Complete.
                </p>
                <button
                    onClick={handleDownload}
                    className="w-full flex items-center justify-center rounded-md bg-green-600 px-3 py-2 text-white text-sm font-semibold hover:bg-green-700"
                >
                    <Download className="mr-2 h-4 w-4" />
                    Download File ({qcResultMeta.name})
                </button>
            </div>
        )}

        {/* --- DATA GRID TABLE VIEW (Uses RTK Query data) --- */}
        {/* 🚨 FIX: Use summaryData for the rows */}
        {(combinedStatus !== 'idle' && !localError) && (
          <div className={`h-[500px] w-full ${(!summaryData || summaryData.summaries?.length === 0) && combinedStatus === 'complete' ? 'hidden' : ''}`}>
              <DataGrid
                          // 🚨 FIX 1: Correctly access the nested 'summaries' array
                          rows={summaryData?.summaries || mockSummary} 
                          
                          // 🚨 FIX 2: Pass the defined columns
                          columns={getSummaryColumns(isDarkMode)} 
                          
                          // 🚨 FIX 3: Add getRowId if your IDs are numbers (which they are)
                          getRowId={(row) => row.id} 
                          
                          // ... rest of DataGrid config (copied from your old mock) ...
                          initialState={{
                              pagination: { paginationModel: { pageSize: 7 } },
                          }}
                          pageSizeOptions={[5, 7, 10]}
                          disableRowSelectionOnClick
                          className={dataGridClassNames}
                          sx={dataGridSxStyles(isDarkMode)} // Assuming you import this
                      />
                  </div>
              )}
        {/* --- END DATA GRID TABLE VIEW --- */}
        
        {/* --- DOWNLOAD BUTTON (Appears on successful completion) --- */}
        {combinedStatus === 'complete' && qcResultMeta && (
            <button
                onClick={handleDownload}
                className="w-full flex items-center justify-center rounded-md bg-green-500 px-4 py-3 text-white font-semibold hover:bg-green-600 mt-4"
            >
                <Download className="mr-2 h-5 w-5" />
                Download Processed QC File ({qcResultMeta.name})
            </button>
        )}
        
        {/* 🚨 FIX: Check against summaryData length for the "No issues" message */}
        {combinedStatus === 'complete' && (summaryData?.summaries?.length === 0) && (
            <div className="p-8 text-center bg-yellow-50 rounded-lg dark:bg-yellow-900/50 dark:text-yellow-200">
                No issues detected or no relevant checks were run.
            </div>
        )}
      </div>
    </div>
  );
};

export default BoardView;