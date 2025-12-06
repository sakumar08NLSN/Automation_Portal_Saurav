import React, { useState, useEffect } from "react";
import { Upload, X, CheckCircle, AlertTriangle, FileText, Loader, Download } from "lucide-react";
// import { DataGrid, GridColDef, GridRowId } from "@mui/x-data-grid";
import { useAppSelector } from "@/app/redux"; 
import { dataGridClassNames, dataGridSxStyles } from "@/lib/utils"; 
// 💡 IMPORT THE NEW RTK QUERY HOOK AND INTERFACE
import { useRunQcChecksMutation, QcSummaryResult, useRunMarketChecksMutation } from "@/state/api"; 


// NOTE: QcRunResponse is now defined globally for consistency
export interface QcRunResponse {
    status: string;
    message: string;
    download_url: string;
    summaries: QcSummaryResult[];
}


// --- MOCK DATA FOR AVAILABLE CHECKS (Must match backend market_check_map keys) ---
const availableChecks = [
    // --- Integrity / Review Checks ---
    { key: "check_italy_mexico", name: "Channel/Market Duplication Check", type: "Review" },
    { key: "check_f1_obligations", name: "F1 Broadcaster Obligation Check", type: "Review" },
    { key: "duration_limits", name: "Duration Limits (5m-5h) Check", type: "Integrity" },
    { key: "live_date_integrity", name: "Live Session Date Integrity", type: "Integrity" },
    { key: "check_session_completeness", name: "Session Count Completeness", type: "Integrity" },
    { key: "update_audience_from_overnight", name: "Update Audience from Overnight Max", type: "Modeling" },
    { key: "apply_duplication_weights", name: "Apply Market Duplication Weights", type: "Modeling" },

    // --- Removal Checks ---
    { key: "remove_andorra", name: "Remove Andorra Data", type: "Removal" },
    { key: "remove_serbia", name: "Remove Serbia Data", type: "Removal" },
    { key: "remove_montenegro", name: "Remove Montenegro Data", type: "Removal" },
    { key: "remove_brazil_espn_fox", name: "Remove Brazil ESPN/FOX Duplicates", type: "Removal" },
];

type ListViewProps = {
  id: string;
  setIsModalNewTaskOpen: (isOpen: boolean) => void;
};


const ListView = ({ id, setIsModalNewTaskOpen }: ListViewProps) => {
  // 💡 RTK QUERY: Initialize the mutation hook
  // We MUST type the data return as QcRunResponse for correct property access
  const [runQc, { 
    isLoading, 
    isSuccess, 
    isError, 
    error, 
    data: summaryData 
}] = useRunMarketChecksMutation();


  // --- FILE STATE ---
  const [selectedBSRFile, setSelectedBSRFile] = useState<File | null>(null);
  const [selectedRoscoFile, setSelectedRoscoFile] = useState<File | null>(null);
  const [selectedDataFile, setSelectedDataFile] = useState<File | null>(null); 
  const [selectedMacroFile, setSelectedMacroFile] = useState<File | null>(null); 

  // --- PROCESSING & UI STATE ---
  const [selectedChecks, setSelectedChecks] = useState<string[]>([]);
  const [processStatus, setProcessStatus] = useState<'idle' | 'complete' | 'error'>('idle');
  const [localError, setLocalError] = useState<string | null>(null);
  // Stores the download URL and filename from the JSON response
  const [qcResultMeta, setQcResultMeta] = useState<{url: string, name: string} | null>(null);
  // Store the validation rows for the DataGrid
  const [validationResults, setValidationResults] = useState<QcSummaryResult[] | null>(null);
  

  const isDarkMode = useAppSelector((state) => state.global.isDarkMode);

  const isReadyToRun = selectedBSRFile && selectedRoscoFile && selectedChecks.length > 0;
  const isProcessingComplete = processStatus === 'complete';

  // 💡 COMBINED STATUS: Controls the UI flows (loading/complete/error)
  const combinedStatus = isLoading ? 'loading' : isProcessingComplete ? 'complete' : localError ? 'error' : 'idle';
  
  

  // --- MOCK SUMMARY DATA (Fallback for table) ---
  const mockSummary: QcSummaryResult[] = [
    { id: 1, description: "Period Integrity Check", action: "Audit", status: "Completed", total_issues_flagged: 0 }, 
    { id: 2, description: "Field Completeness Check", action: "Audit", status: "Issue Found", total_issues_flagged: 15 },
  ];

  // --- EFFECT TO HANDLE RTK QUERY RESPONSE (Success and Error) ---
  useEffect(() => {
    // 1. Check for success and ensure data exists
    if (isSuccess && summaryData) {
      // 🚨 CRUCIAL: Cast summaryData to the EXPECTED type (QcRunResponse)
      // This is needed because the backend sends the entire object, not just the summaries array.
      const response = summaryData as QcRunResponse; 

      // 2. UPDATE STATUS & ERROR
      setProcessStatus('complete');
      setLocalError(null);
      
      // 3. SET DOWNLOAD METADATA
      const urlParams = new URLSearchParams(response.download_url.split('?')[1]);
      // Use the filename provided by the backend, or a default
      const filename = urlParams.get('filename') || `QC_Result_${new Date().toISOString()}.xlsx`;

      setQcResultMeta({
         url: response.download_url, 
         name: filename
      });
      
      // 4. SET TABLE DATA
      // Store the nested summaries array
      setValidationResults(response.summaries); 

    } else if (isError) {
      // 1. UPDATE STATUS & ERROR
      setProcessStatus('error');
      // Use the RTK Query error payload for detailed messages
      setLocalError(`❌ API Error: ${(error as any).data?.detail || 'Processing failed. Check console/network logs.'}`);
      setQcResultMeta(null);
      setValidationResults(null);
    }
}, [isSuccess, isError, summaryData, error]);
    
  
  // --- 1. RTK QUERY TRIGGER LOGIC ---
  const handleRunChecks = async () => {
    if (!isReadyToRun || isLoading) return;
    
    setProcessStatus('idle'); 
    setLocalError(null);
    setQcResultMeta(null); 
    setValidationResults(null); // Clear previous table data

    const formData = new FormData();
    // 💡 REMINDER: We are mapping Rosco/Macro to the specific Market Check field names
    formData.append('bsr_file', selectedBSRFile as File);
    if (selectedRoscoFile) { formData.append('obligation_file', selectedRoscoFile); } // Rosco -> Obligation
    if (selectedMacroFile) { formData.append('overnight_file', selectedMacroFile); } // Macro -> Overnight
    // formData.append('data_file', selectedDataFile as File); // This field is not in the market_check API

    // Ensure the checks list is sent as a JSON string
    formData.append('checks', JSON.stringify(selectedChecks));

    try {
      await runQc(formData).unwrap();
    } catch (err) {
      // Error handled in the useEffect hook above
      console.error("QC Check execution failed:", err);
    }
  };

  // --- 2. DOWNLOAD HANDLER (Uses the URL Metadata) ---
  const handleDownload = () => {
    if (!qcResultMeta) return;

    const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/';
    
    // Construct the full URL for the GET request
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
        <div className="flex flex-col md:flex-row md:space-x-6 space-y-6 md:space-y-0">
            
            {/* 💡 LEFT SIDE: CHECKLIST */}
            <div className="flex-1 space-y-4 pt-0">
                <h3 className="text-xl font-bold dark:text-white">Select Checks</h3>
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

            {/* 💡 RIGHT SIDE: FILE UPLOADS */}
            <div className="flex-1 space-y-4 pt-0">
                <h3 className="text-xl font-bold dark:text-white">QC File Selection</h3>
                
                {/* --- FIRST HORIZONTAL ROW (BSR and ROSCO/Obligation) --- */}
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

                    {/* ROSCO/OBLIGATION File (Mandatory for ready, Mapped to 'obligation_file') */}
                    <div className="flex-1">
                        <p className="font-medium text-gray-700 dark:text-gray-300">Obligation File (Rosco) (Mandatory)</p>
                        <label className="flex flex-col items-center justify-center border-2 border-dashed border-green-300 p-4 cursor-pointer rounded-lg bg-green-50 dark:bg-green-950/50 h-full">
                            <FileText className="h-8 w-8 text-green-600" />
                            <p  className="mt-2 text-sm text-green-600 dark:text-green-300 text-center">{selectedRoscoFile ? selectedRoscoFile.name : "Upload Obligation/Rosco (.xlsx)"}</p>
                            <input type="file" className="hidden" accept=".xlsx" onChange={(e) => handleFileChange(e, 'rosco')} />
                        </label>
                    </div>
                </div>

                {/* --- SECOND HORIZONTAL ROW (Data File and Macro/Overnight File) --- */}
                <div className="flex space-x-4 pt-4"> 
                    {/* DATA File (Optional - UNUSED by current market_check API) */}
                    <div className="flex-1">
                        <p className="font-medium text-gray-700 dark:text-gray-300">Client Data File (Optional)</p>
                        <label className={`flex flex-col items-center justify-center p-4 cursor-pointer rounded-lg border-2 border-dashed h-full
                                            ${selectedDataFile ? 'border-yellow-500 bg-yellow-50 dark:bg-yellow-900/50' : 'border-gray-300 bg-gray-50 dark:bg-gray-800'}`}>
                            <FileText className={`h-8 w-8 ${selectedDataFile ? 'text-yellow-700' : 'text-gray-500'}`} />
                            <p className={`mt-2 text-sm text-center ${selectedDataFile ? 'text-yellow-700' : 'text-gray-500'} dark:text-gray-400`}>{selectedDataFile ? selectedDataFile.name : "Upload Client Data (.xlsx)"}</p>
                            <input type="file" className="hidden" accept=".xlsx" onChange={(e) => handleFileChange(e, 'data')} />
                        </label>
                    </div>

                    {/* MACRO/OVERNIGHT File (Optional, Mapped to 'overnight_file') */}
                    <div className="flex-1">
                        <p className="font-medium text-gray-700 dark:text-gray-300">Overnight File (Optional)</p>
                        <label className={`flex flex-col items-center justify-center p-4 cursor-pointer rounded-lg border-2 border-dashed h-full
                                            ${selectedMacroFile ? 'border-purple-500 bg-purple-50 dark:bg-purple-900/50' : 'border-gray-300 bg-gray-50 dark:bg-gray-800'}`}>
                            <FileText className={`h-8 w-8 ${selectedMacroFile ? 'text-purple-700' : 'text-gray-500'}`} />
                            <p className={`mt-2 text-sm text-center ${selectedMacroFile ? 'text-purple-700' : 'text-gray-500'} dark:text-gray-400`}>{selectedMacroFile ? selectedMacroFile.name : "Upload Overnight/Macro (.xlsm/.xlsx)"}</p>
                            <input type="file" className="hidden" accept=".xlsm,.xlsx" onChange={(e) => handleFileChange(e, 'macro')} />
                        </label>
                    </div>
                </div>
            </div>
        </div>
        {/* 💡 END: HORIZONTAL CONTAINER FOR CHECKLIST & UPLOADS */}

        
        {/* RUN BUTTON (Spans full width below the horizontal section) */}
        <button
          onClick={handleRunChecks}
          disabled={!isReadyToRun || combinedStatus === 'loading'}
          className="w-full flex items-center justify-center rounded-md bg-blue-500 px-4 py-2 text-white font-semibold hover:bg-blue-600 disabled:bg-gray-400 mt-4"
        >
          {combinedStatus === 'loading' ? (
            <>
              <Loader className="mr-2 h-5 w-5 animate-spin" />
              Running Checks...
            </>
          ) : combinedStatus === 'complete' ? ( // 💡 Display success message
            <>
              <CheckCircle className="mr-2 h-5 w-5" />
              Checks Successful!
            </>
          ) : (
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
        
        {/* DOWNLOAD SUCCESS MESSAGE */}
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
        {(combinedStatus !== 'idle' && !localError) && (
          <div className={`h-[500px] w-full ${(!summaryData || summaryData.summaries?.length === 0) && combinedStatus === 'complete' ? 'hidden' : ''}`}>
             {/* <DataGrid
                rows={summaryData?.summaries || mockSummary} // Use RTK Query data or mock
                columns={getSummaryColumns(isDarkMode)}
                // ... rest of DataGrid config
             /> */}
          </div>
        )}
        {/* --- END DATA GRID TABLE VIEW --- */}
        
        {/* --- DOWNLOAD BUTTON (Final check, redundancy for visibility) --- */}
        {combinedStatus === 'complete' && qcResultMeta && (
            <button
                onClick={handleDownload}
                className="w-full flex items-center justify-center rounded-md bg-green-500 px-4 py-3 text-white font-semibold hover:bg-green-600 mt-4"
            >
                <Download className="mr-2 h-5 w-5" />
                Download Processed QC File ({qcResultMeta.name})
            </button>
        )}
        
        {/* "No issues detected" message */}
        {combinedStatus === 'complete' && (summaryData?.summaries?.length === 0) && (
            <div className="p-8 text-center bg-yellow-50 rounded-lg dark:bg-yellow-900/50 dark:text-yellow-200">
                No issues detected or no relevant checks were run.
            </div>
        )}
      </div>
    </div>
  );
};

export default ListView;