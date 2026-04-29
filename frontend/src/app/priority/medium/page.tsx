"use client";

import { 
  CheckCircle, 
  Download, 
  FileText, 
  Loader, 
  AlertCircle,
  UploadCloud,
  FileSpreadsheet,
  Terminal,
  Globe,
  Database,
  Settings2,
  ChevronDown,
  Search
} from "lucide-react";
import React, { useState, useEffect, useRef } from "react";
import { useOktaAuth } from '@okta/okta-react';

// --- CUSTOM DROPDOWN COMPONENT ---
const CustomDropdown = ({ label, value, options, onChange }: { label: string, value: string, options: string[], onChange: (val: string) => void }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const filteredOptions = options.filter(opt => 
    opt.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div ref={dropdownRef} className="relative w-full">
      <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-1.5">
        {label}
      </label>
      <div 
        onClick={() => setIsOpen(!isOpen)}
        className={`w-full bg-slate-50 dark:bg-[#0B0F1A] border ${isOpen ? 'border-indigo-500 ring-1 ring-indigo-500' : 'border-slate-200 dark:border-slate-800'} text-slate-900 dark:text-slate-100 rounded-lg px-3 py-2 text-xs cursor-pointer flex items-center justify-between transition-all duration-200`}
      >
        <span className="truncate">{value}</span>
        <ChevronDown size={14} className={`text-slate-400 transition-transform duration-300 ${isOpen ? 'rotate-180' : ''}`} />
      </div>

      {/* Dropdown Menu - Added Scrollbar and Search */}
      <div className={`absolute left-0 right-0 z-50 mt-1 origin-top transition-all duration-200 ease-out bg-white dark:bg-[#161B26] border border-slate-200 dark:border-slate-800 rounded-lg shadow-2xl overflow-hidden ${isOpen ? 'opacity-100 scale-y-100 translate-y-0 visible' : 'opacity-0 scale-y-95 -translate-y-2 invisible'}`}>
        <div className="p-2 border-b border-slate-100 dark:border-slate-800 flex items-center gap-2">
          <Search size={12} className="text-slate-400" />
          <input 
            type="text" 
            placeholder="Search..." 
            className="w-full bg-transparent text-[11px] outline-none text-slate-600 dark:text-slate-300"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
        <ul className="max-h-60 overflow-y-auto scrollbar-thin scrollbar-thumb-slate-300 dark:scrollbar-thumb-slate-700 py-1">
          {filteredOptions.length > 0 ? filteredOptions.map((opt) => (
            <li 
              key={opt}
              onClick={() => { onChange(opt); setIsOpen(false); setSearchTerm(""); }}
              className={`px-3 py-2 text-xs cursor-pointer transition-colors ${value === opt ? 'bg-indigo-50 dark:bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 font-bold' : 'text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'}`}
            >
              {opt}
            </li>
          )) : (
            <li className="px-3 py-4 text-[10px] text-center text-slate-500 italic">No matches found</li>
          )}
        </ul>
      </div>
    </div>
  );
};

const IntlRateCalculator = () => {
  const { oktaAuth } = useOktaAuth();
  const [files, setFiles] = useState<{ intl: File | null; cpm: File | null; euro: File | null; }>({ intl: null, cpm: null, euro: null });
  const [sportGenre, setSportGenre] = useState<string>("Football");
  const [spotFixture, setSpotFixture] = useState<string>("0");
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<'idle' | 'complete' | 'error'>('idle');
  const [error, setError] = useState<string | null>(null);
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
  const [logs, setLogs] = useState<string[]>([]);
  const [timestamp, setTimestamp] = useState<string | null>(null);

  const scrollRef = useRef<HTMLDivElement>(null);
  const isReady = !!(files.intl && files.cpm && files.euro);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [logs]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>, key: keyof typeof files) => {
    const file = e.target.files?.[0] || null;
    setFiles(prev => ({ ...prev, [key]: file }));
    setStatus('idle');
    if (file) setLogs(prev => [...prev, `FILE UPLOADED: ${file.name}`]);
  };

  const handleDownload = () => {
    if (!downloadUrl) return;
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = `Intl_Audit_Results_${Date.now()}.xlsx`;
    link.click();
  };

  const handleRunCalculation = async () => {
    if (!isReady || loading) return;
    setLoading(true);
    setStatus('idle');
    setDownloadUrl(null);
    setLogs(["Initializing engines...", `Configuring session for ${sportGenre}...`]);

    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, ""); 
      const token = oktaAuth?.getAccessToken();
      const headers: HeadersInit = token ? { "Authorization": `Bearer ${token}` } : {};

      const formData = new FormData();
      formData.append('intl_data', files.intl!);
      formData.append('cpm_file', files.cpm!);
      formData.append('euro_file', files.euro!);
      formData.append('sport_genre', sportGenre);
      formData.append('spot_fixture', spotFixture);

      const response = await fetch(`${baseUrl}/qc/calculate_intl_final_audit`, {
        method: 'POST',
        body: formData,
        headers: headers,
      });

      if (!response.body) throw new Error("No response body from server.");
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let streamBuffer = ""; 

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        streamBuffer += decoder.decode(value, { stream: true });
        const parts = streamBuffer.split("\n\n");
        streamBuffer = parts.pop() || "";
        for (const part of parts) {
          const trimmedLine = part.trim();
          if (trimmedLine.startsWith("data: ")) setLogs(prev => [...prev, trimmedLine.replace("data: ", "")]);
          else if (trimmedLine.startsWith("file: ")) {
            const base64Data = trimmedLine.substring(6).replace(/\s/g, ""); 
            const byteCharacters = atob(base64Data);
            const byteNumbers = new Array(byteCharacters.length);
            for (let i = 0; i < byteCharacters.length; i++) byteNumbers[i] = byteCharacters.charCodeAt(i);
            const blob = new Blob([new Uint8Array(byteNumbers)], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
            setDownloadUrl(URL.createObjectURL(blob));
            setTimestamp(new Date().toLocaleTimeString());
            setStatus('complete');
          }
        }
      }
    } catch (err: any) {
      setError("Calculation failed.");
      setLogs(prev => [...prev, `CRITICAL ERROR: ${err.message}`]);
    } finally {
      setLoading(false);
    }
  };

  const sportOptions = ["American Football", "Basketball", "Boxing", "Cricket", "Cycling", "Football", "Golf", "Horse Racing", "Hockey", "Motorsport", "Rugby", "Sailing", "Tennis", "General", "Wintersport", "Niche", "Cycling_Giro_Vuelta", "Cycling_Tour de France", "Sportainment", "Alpine Skiing", "Chinese Super League", "Badminton"];

  return (
    <div className="flex flex-col w-full h-screen bg-[#FDFDFD] dark:bg-[#08090A] overflow-hidden text-slate-900 dark:text-slate-100">
      <header className="w-full px-6 py-4 border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-[#0B0F1A] flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-indigo-600 rounded-lg shadow-lg">
            <Globe className="h-5 w-5 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-black tracking-tight leading-none italic text-indigo-600 dark:text-indigo-400">INTL RATE ENGINE</h1>
            <p className="text-[10px] text-slate-500 font-bold uppercase tracking-[0.2em] mt-1">Advanced Logistics Processor</p>
          </div>
        </div>
      </header>

      <main className="flex-1 flex flex-col p-6 gap-6 min-h-0 max-w-[1600px] mx-auto w-full">
        {/* FILE UPLOAD GRID */}
        <div className="grid grid-cols-3 gap-6 shrink-0">
          {[
            { id: 'intl', label: 'Rates + Ratings Data', icon: FileSpreadsheet, color: 'text-indigo-500' },
            { id: 'cpm', label: 'CPM Macro File', icon: FileText, color: 'text-amber-500' },
            { id: 'euro', label: 'EURO Macro File', icon: Database, color: 'text-emerald-500' }
          ].map((item) => (
            <label key={item.id} className={`flex items-center gap-4 px-5 h-20 border-2 rounded-2xl cursor-pointer transition-all ${files[item.id as keyof typeof files] ? 'border-indigo-500 bg-indigo-50/30 dark:bg-indigo-500/5' : 'border-dashed border-slate-200 dark:border-slate-800 hover:border-indigo-400 dark:hover:border-indigo-500 bg-white dark:bg-[#11141D]'}`}>
              <input type="file" id={item.id} className="hidden" onChange={(e) => handleFileChange(e, item.id as keyof typeof files)} />
              <div className={`p-3 rounded-xl bg-white dark:bg-[#0B0F1A] ${item.color} shadow-sm border border-slate-100 dark:border-slate-800`}>
                <item.icon size={22} />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-xs font-bold truncate uppercase tracking-tight">{files[item.id as keyof typeof files]?.name || item.label}</p>
                <p className="text-[10px] text-slate-400 font-semibold">{files[item.id as keyof typeof files] ? 'FILE READY' : 'CLICK TO UPLOAD'}</p>
              </div>
            </label>
          ))}
        </div>

        {/* WORKSPACE */}
        <div className="grid grid-cols-4 gap-6 flex-1 min-h-0">
          {/* CONFIGURATION */}
          <div className="col-span-1 bg-white dark:bg-[#11141D] border border-slate-200 dark:border-slate-800 rounded-3xl p-6 flex flex-col shadow-xl">
            <div className="flex items-center gap-2 mb-6 border-b border-slate-100 dark:border-slate-800 pb-4">
              <Settings2 size={18} className="text-indigo-500" />
              <h2 className="text-xs font-black uppercase tracking-[0.15em]">Processing Config</h2>
            </div>

            <div className="space-y-6 flex-1">
              <div className="relative z-30">
                <CustomDropdown label="Sport Genre" value={sportGenre} options={sportOptions} onChange={setSportGenre} />
              </div>
              <div className="relative z-20">
                <CustomDropdown label="CPT Floor Factor (%)" value={spotFixture} options={["0", "20"]} onChange={setSpotFixture} />
              </div>
            </div>
            
            <button
              onClick={handleRunCalculation}
              disabled={!isReady || loading}
              className={`w-full py-4 mt-8 rounded-2xl font-black text-xs tracking-widest transition-all flex items-center justify-center gap-3 shadow-lg hover:translate-y-[-2px] active:translate-y-[0px] ${status === 'complete' ? 'bg-emerald-500 text-white' : 'bg-indigo-600 text-white disabled:bg-slate-100 dark:disabled:bg-slate-800 disabled:text-slate-400'}`}
            >
              {loading ? <><Loader className="animate-spin" size={18} /> PROCESSING</> : <><UploadCloud size={18} /> RUN CALCULATION</>}
            </button>
          </div>

          {/* CONSOLE & EXPORT */}
          <div className="col-span-3 bg-slate-950 border border-slate-800 rounded-3xl flex flex-col shadow-2xl overflow-hidden ring-1 ring-slate-800/50">
            <div className="px-5 py-4 bg-[#0B0F1A] border-b border-slate-800 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className={`h-2 w-2 rounded-full ${loading ? 'bg-emerald-500 animate-pulse' : 'bg-slate-600'}`} />
                <span className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-400 flex items-center gap-2"><Terminal size={14} /> System Terminal</span>
              </div>
              
              {/* VIBRANT EXPORT BUTTON - Highly Visible */}
              {status === 'complete' && downloadUrl && (
                <button 
                  onClick={handleDownload}
                  className="bg-emerald-500 hover:bg-emerald-400 text-white px-4 py-2 rounded-xl text-[10px] font-black flex items-center gap-2 shadow-lg animate-bounce-short transition-all"
                >
                  <Download size={14} /> SAVE EXPORT (.XLSX)
                </button>
              )}
            </div>

            <div ref={scrollRef} className="flex-1 p-6 font-mono text-[12px] overflow-y-auto space-y-2 scrollbar-thin scrollbar-thumb-slate-800">
              {logs.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-slate-700 opacity-50">
                  <Terminal size={40} className="mb-4" />
                  <p className="uppercase tracking-widest font-bold">Waiting for input...</p>
                </div>
              ) : (
                logs.map((log, i) => (
                  <div key={i} className="flex gap-4 border-l-2 border-slate-800 pl-3 py-0.5 hover:bg-slate-900/50 transition-colors">
                    <span className="text-slate-600 shrink-0 font-bold">{new Date().toLocaleTimeString([], {hour12: false})}</span>
                    <span className={log.includes('ERROR') ? 'text-rose-400' : log.includes('FILE') ? 'text-indigo-400' : 'text-slate-300'}>
                      {log}
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default IntlRateCalculator;