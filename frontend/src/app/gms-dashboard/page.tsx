"use client";

import React, { useState, useMemo } from "react";
import { 
  Search, Filter, Clock, AlertCircle, CheckCircle2, User, Hash,
  Activity, CalendarDays, ChevronRight, ShieldCheck, X, BarChart3, MapPin, FileText,
  TrendingUp, Users, Target, Info, Briefcase, AlertTriangle, RefreshCw, 
  ChevronLeft, ChevronRight as ChevronRightIcon, PieChart as PieChartIcon, Zap, Layers,
  Trophy, Globe, FileBarChart, Network, PlayCircle, Flag, AlignLeft, FastForward, Scale, ChevronDown
} from "lucide-react";
import { useGetDeliveryDashboardQuery } from "@/state/api"; 
import { 
  ComposedChart, Line, BarChart, Bar, PieChart, Pie, Cell, 
  XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, 
  ResponsiveContainer, Legend, LabelList, ScatterChart, Scatter, ZAxis,
  AreaChart, Area
} from "recharts";

// --- HELPER FUNCTIONS ---
const truncateText = (text: string, maxLength: number = 14) => (!text ? "" : text.length > maxLength ? text.substring(0, maxLength) + "..." : text);
const formatLargeNumber = (num: number) => num >= 1000000 ? (num / 1000000).toFixed(1) + 'M' : num >= 1000 ? (num / 1000).toFixed(1) + 'k' : num.toString();

const InfoTooltip = ({ text, align = "center", position = "top" }: { text: string, align?: "center" | "left" | "right", position?: "top"|"bottom" }) => {
  const posClasses = position === "top" ? "bottom-full mb-2" : "top-full mt-2";
  const alignClasses = align === "left" ? "left-0" : align === "right" ? "right-0" : "left-1/2 -translate-x-1/2";
  const arrowClasses = position === "top" ? "top-full border-t-slate-800 dark:border-t-slate-700" : "bottom-full border-b-slate-800 dark:border-b-slate-700";
  const arrowAlignClasses = align === "left" ? "left-2" : align === "right" ? "right-2" : "left-1/2 -translate-x-1/2";

  return (
    <span className="relative group inline-flex items-center justify-center ml-1.5 cursor-help z-50">
      <Info size={12} className="text-slate-400 group-hover:text-blue-500 transition-colors" />
      <span className={`absolute ${posClasses} ${alignClasses} hidden group-hover:block w-52 p-2 bg-slate-800 dark:bg-slate-700 text-white text-[10px] leading-relaxed rounded-lg shadow-xl font-normal normal-case tracking-normal pointer-events-none z-[100] whitespace-normal`}>
        {text}
        <span className={`absolute ${arrowClasses} ${arrowAlignClasses} border-4 border-transparent`}></span>
      </span>
    </span>
  );
};

// --- CUSTOM STYLED DROPDOWN COMPONENT ---
const CustomDropdown = ({ value, onChange, options, defaultLabel, icon: Icon }: any) => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div 
      className="relative w-full sm:w-auto" 
      tabIndex={0} 
      onBlur={(e) => {
        if (!e.currentTarget.contains(e.relatedTarget as Node)) setIsOpen(false);
      }}
    >
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center justify-between w-full sm:w-auto min-w-[140px] gap-2 bg-slate-50 dark:bg-[#0B0F1A] border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-xs font-bold text-slate-700 dark:text-slate-300 transition-colors hover:border-blue-400 dark:hover:border-blue-500"
      >
        <div className="flex items-center gap-2">
          {Icon && <Icon size={14} className="text-slate-400" />}
          <span className="truncate max-w-[120px]">
            {value === "ALL" ? defaultLabel : (options.find((o:any) => (o.val || o) === value)?.label || value)}
          </span>
        </div>
        <ChevronDown size={14} className={`text-slate-400 transition-transform ${isOpen ? "rotate-180" : ""}`} />
      </button>
      
      {isOpen && (
        <div className="absolute top-full left-0 mt-1 w-full min-w-[160px] bg-white dark:bg-[#111623] border border-slate-200 dark:border-slate-700 rounded-lg shadow-2xl z-50 max-h-60 overflow-y-auto custom-scrollbar flex flex-col py-1">
          <div 
            className={`px-3 py-2 text-xs font-bold cursor-pointer transition-colors ${value === "ALL" ? "bg-blue-50 text-blue-600 dark:bg-blue-500/10 dark:text-blue-400" : "text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800"}`}
            onClick={() => { onChange("ALL"); setIsOpen(false); }}
          >
            {defaultLabel}
          </div>
          {options.map((opt: any) => {
            const isObj = typeof opt === 'object';
            const val = isObj ? opt.val : opt;
            const label = isObj ? opt.label : opt;
            const isSelected = value === val;

            return (
              <div 
                key={val}
                className={`px-3 py-2 text-xs font-bold cursor-pointer transition-colors ${isSelected ? "bg-blue-50 text-blue-600 dark:bg-blue-500/10 dark:text-blue-400" : "text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800"}`}
                onClick={() => { onChange(val); setIsOpen(false); }}
              >
                {label}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

// --- CUSTOM TOOLTIPS FOR CHARTS ---
const SlaTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload; 
    return (
      <div className="bg-white dark:bg-[#111623] border border-slate-200 dark:border-slate-800 p-3 rounded-lg shadow-xl z-50 min-w-[180px]">
        <p className="text-[10px] font-black uppercase tracking-wider text-slate-400 mb-2 border-b border-slate-100 dark:border-slate-800 pb-1">{label} Details</p>
        <div className="flex flex-col gap-1.5">
          <p className="text-xs font-black flex items-center justify-between gap-4 text-emerald-500"><span>SLA Met Rate</span><span>{data.slaRate}%</span></p>
          <p className="text-[10px] font-bold flex items-center justify-between gap-4 text-slate-600 dark:text-slate-300"><span>Total Volume</span><span>{data.volume}</span></p>
          <p className="text-[10px] font-bold flex items-center justify-between gap-4 text-emerald-600 dark:text-emerald-400"><span>Total Met</span><span>{data.met}</span></p>
          <p className="text-[10px] font-bold flex items-center justify-between gap-4 text-slate-400 dark:text-slate-500"><span>Total Pending</span><span>{data.pending}</span></p>
          <p className="text-[10px] font-bold flex items-center justify-between gap-4 text-rose-500"><span>Total Missed</span><span>{data.missed}</span></p>
        </div>
      </div>
    );
  }
  return null;
};

const RoscoTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload; 
    return (
      <div className="bg-white dark:bg-[#111623] border border-slate-200 dark:border-slate-800 p-3 rounded-lg shadow-xl z-50 min-w-[200px]">
        <p className="text-[10px] font-black uppercase tracking-wider text-slate-400 mb-2 border-b border-slate-100 dark:border-slate-800 pb-1">Delivery ID: <span className="text-slate-700 dark:text-slate-200">{label}</span></p>
        <div className="flex flex-col gap-1.5">
          <p className="text-[10px] font-bold flex items-center justify-between gap-4 text-slate-600 dark:text-slate-300"><span className="flex items-center gap-1"><User size={10} className="text-emerald-500"/> FTE Assigned</span><span>{data.fte}</span></p>
          <p className="text-[10px] font-bold flex items-center justify-between gap-4 text-slate-600 dark:text-slate-300"><span className="flex items-center gap-1"><CalendarDays size={10} className="text-blue-500"/> Date</span><span>{data.date}</span></p>
          
          <div className="h-px w-full bg-slate-100 dark:bg-slate-800 my-1"></div>
          
          <p className="text-[10px] font-bold flex items-center justify-between gap-4 text-slate-400"><span>Expected Effort</span><span>{data.expectedEffort} hrs</span></p>
          <p className="text-[10px] font-bold flex items-center justify-between gap-4 text-purple-500"><span>Actual Spent</span><span>{data.actualSpent} hrs</span></p>
          
          <div className="h-px w-full bg-slate-100 dark:bg-slate-800 my-1"></div>

          <p className="text-[10px] font-bold flex items-center justify-between gap-4 text-rose-500">
            <span>Delay Status</span>
            <span className={`flex items-center gap-1 ${data.delayDays > 0 ? 'text-rose-500' : 'text-emerald-500'}`}>
                {data.delayDays > 0 ? <AlertTriangle size={10}/> : <CheckCircle2 size={10}/>}
                {data.delayDays > 0 ? `Late (${data.delayDays}d)` : "No"}
            </span>
          </p>
          <p className="text-[10px] font-bold flex items-center justify-between gap-4 text-indigo-500">
            <span>Early Status</span>
            <span className={`flex items-center gap-1 ${data.daysSaved > 0 ? 'text-indigo-500' : 'text-slate-400'}`}>
                {data.daysSaved > 0 ? <FastForward size={10}/> : <CheckCircle2 size={10}/>}
                {data.daysSaved > 0 ? `Saved (${data.daysSaved}d)` : "No"}
            </span>
          </p>
          <p className="text-[10px] font-bold flex items-center justify-between gap-4 text-amber-500">
            <span>Rework Status</span>
            <span className={`flex items-center gap-1 ${data.isRework ? 'text-amber-500' : 'text-slate-400'}`}>
                {data.isRework ? <RefreshCw size={10}/> : <CheckCircle2 size={10}/>}
                {data.isRework ? "Yes" : "No"}
            </span>
          </p>
        </div>
      </div>
    );
  }
  return null;
};

const WorkloadTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload; 
    return (
      <div className="bg-white dark:bg-[#111623] border border-slate-200 dark:border-slate-800 p-3 rounded-lg shadow-xl z-50 min-w-[200px]">
        <p className="text-[10px] font-black uppercase tracking-wider text-slate-400 mb-2 border-b border-slate-100 dark:border-slate-800 pb-1">{label} Volume Details</p>
        <div className="flex flex-col gap-1.5">
          <p className="text-[10px] font-bold flex items-center justify-between gap-4 text-blue-500"><span>Total Lines Evaluated</span><span>{formatLargeNumber(data.totalLines)}</span></p>
          <p className="text-[10px] font-bold flex items-center justify-between gap-4 text-rose-500"><span>In Scope (Our Error)</span><span>{formatLargeNumber(data.inScopeLines)}</span></p>
          <div className="h-px w-full bg-slate-100 dark:bg-slate-800 my-1"></div>
          <p className="text-[10px] font-bold flex items-center justify-between gap-4 text-emerald-500"><span>Rework: In-Scope</span><span>{data.inScopeReworkPct}%</span></p>
          <p className="text-[10px] font-bold flex items-center justify-between gap-4 text-purple-500"><span>Rework: Out-of-Scope</span><span>{data.outScopeReworkPct}%</span></p>
        </div>
      </div>
    );
  }
  return null;
};

const ScatterTooltip = ({ active, payload }: any) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload; 
    return (
      <div className="bg-white dark:bg-[#111623] border border-slate-200 dark:border-slate-800 p-3 rounded-lg shadow-xl z-50 min-w-[200px]">
        <p className="text-[10px] font-black uppercase tracking-wider text-slate-400 mb-2 border-b border-slate-100 dark:border-slate-800 pb-1">
          {data.client} <span className="text-slate-500 font-medium">({data.roscoId})</span>
        </p>
        <div className="flex flex-col gap-1.5">
          <p className="text-[10px] font-bold flex items-center justify-between gap-4 text-blue-500">
            <span>Expected Effort</span><span>{data.expectedEffort} hrs</span>
          </p>
          <p className="text-[10px] font-bold flex items-center justify-between gap-4 text-purple-500">
            <span>Actual Spent</span><span>{data.actualSpent} hrs</span>
          </p>
          <div className="h-px w-full bg-slate-100 dark:bg-slate-800 my-1"></div>
          <p className="text-[10px] font-bold flex items-center justify-between gap-4 text-slate-600 dark:text-slate-300">
            <span>Total Lines</span><span>{formatLargeNumber(data.totalLines)}</span>
          </p>
          <p className="text-[10px] font-bold flex items-center justify-between gap-4 text-rose-500">
            <span>Delay Days</span><span>{data.delayDays}</span>
          </p>
          <p className="text-[10px] font-bold flex items-center justify-between gap-4 text-amber-500">
            <span>Reworks</span><span>{data.reworks}</span>
          </p>
        </div>
      </div>
    );
  }
  return null;
};

const DeliveryDashboard = () => {
  const { data: rawDeliveryData = [], isLoading, isError } = useGetDeliveryDashboardQuery();

  // State
  const [searchTerm, setSearchTerm] = useState("");
  const [filterStatus, setFilterStatus] = useState<"ALL" | "ON_TIME" | "DELAYED" | "REWORK">("ALL");
  const [selectedMonth, setSelectedMonth] = useState<string>("ALL");
  const [selectedDay, setSelectedDay] = useState<string>("ALL");
  const [selectedOffice, setSelectedOffice] = useState<string>("ALL");
  const [selectedSport, setSelectedSport] = useState<string>("ALL");
  const [selectedRecord, setSelectedRecord] = useState<any | null>(null);
  
  // Scatter Plot State
  const [scatterX, setScatterX] = useState("expectedEffort");
  const [scatterY, setScatterY] = useState("actualSpent");


  // Drill-down states
  const [roscoSearch, setRoscoSearch] = useState("");
  const [workloadStartDate, setWorkloadStartDate] = useState("");
  const [workloadEndDate, setWorkloadEndDate] = useState("");
  const [workloadView, setWorkloadView] = useState<"MONTH" | "DAY">("MONTH"); 
  const [daysSavedView, setDaysSavedView] = useState<"TREND" | "PROJECTS">("TREND");

  const [trendView, setTrendView] = useState<"MONTH" | "DAY">("MONTH");
  const [currentPage, setCurrentPage] = useState(1);
  const rowsPerPage = 50;

  

  const SCATTER_METRICS = [
    { val: "expectedEffort", label: "Expected Effort (hrs)" },
    { val: "actualSpent", label: "Actual Spent (hrs)" },
    { val: "totalLines", label: "Total Lines Evaluated" },
    { val: "delayDays", label: "Total Delay Days" },
    { val: "daysSaved", label: "Total Days Saved" },
    { val: "reworks", label: "Total Reworks" }
  ];

  // --- 🧠 STEP 1: BASE DATA NORMALIZATION ---
  const normalizedData = useMemo(() => {
    return rawDeliveryData
      .map((row: any) => {
        const delayDays = Number(row.delay_severity ?? row['Delay \nin days'] ?? 0);
        const isRework = (row['Rework (Yes/No)'] || "").toLowerCase() === 'yes';
        
        let statusGroup = "ON_TIME";
        if (delayDays > 0) statusGroup = "DELAYED";
        if (isRework) statusGroup = "REWORK"; 

        const expectedEffort = Number(row['Expected Effort'] ?? 0);
        const actualSpent = Number(row['Actual Spent'] ?? 0);
        
        const totalLines = Number(row['Total Lines'] ?? row.delivery_metrics?.Workload?.Total_Evaluated ?? 0);
        const inScopeLines = Number(row.delivery_metrics?.Workload?.Passed ?? 0); 
        const outScopeLines = Number(row.delivery_metrics?.Workload?.Failed ?? 0); 

        let baseDate = row.original_delivery_date || row['Original Delivery Date'] || "Unknown";
        let monthYear = "TBD";
        let exactDay = "TBD";
        let sortableDay = "0000-00-00";
        let yearStr = "";

        if (baseDate !== "Unknown" && baseDate !== "discarded" && baseDate.trim() !== "") {
           const d = new Date(baseDate);
           if (!isNaN(d.getTime())) {
             monthYear = d.toLocaleDateString('en-US', { month: 'short', year: '2-digit' });
             exactDay = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
             sortableDay = d.toISOString().split('T')[0];
             yearStr = d.getFullYear().toString();
           }
        }

        let daysSaved = 0;
        let finalSlaStatus = "MISSED"; 

        if (row.original_delivery_date) {
            const orig = new Date(row.original_delivery_date);
            if (row.actual_delivered_date) {
                const act = new Date(row.actual_delivered_date);
                if (!isNaN(orig.getTime()) && !isNaN(act.getTime())) {
                    const diffTime = orig.getTime() - act.getTime();
                    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
                    daysSaved = diffDays > 0 ? diffDays : 0; 
                    finalSlaStatus = act.getTime() <= orig.getTime() ? "MET" : "MISSED";
                }
            } else {
                const today = new Date();
                today.setHours(0, 0, 0, 0);
                if (!isNaN(orig.getTime())) {
                    finalSlaStatus = orig.getTime() < today.getTime() ? "MISSED" : "PENDING";
                }
            }
        }

        return { 
          ...row, 
          _delayDays: delayDays, 
          _isRework: isRework, 
          _statusGroup: statusGroup,
          _expectedEffort: expectedEffort,
          _actualSpent: actualSpent,
          _totalLines: totalLines,
          _inScopeLines: inScopeLines,
          _outScopeLines: outScopeLines,
          _monthYear: monthYear,
          _exactDay: exactDay,
          _sortableDay: sortableDay,
          _year: yearStr, 
          _client: row.client_account || row['Product/Client'] || "Unknown",
          _fte: row.owner_fte || row.FTE || "Unassigned",
          _poc: row.POC || row.manager || "Unassigned",
          _sport: row.Sport || row.sport_category || "Unassigned",
          _office: row.Office || row.office_location || "Unassigned",
          _id: row.tracking_id || row['ROSCO ID'] || "N/A",
          _deliveryId: row.delivery_uid || row['Delivery ID'] || "N/A",
          _reportType: row['Delivery Detail'] || "Standard Report",
          _assignmentStatus: row['Assignment status'] || "Unknown",
          _slaStatus: finalSlaStatus,
          _daysSaved: daysSaved,
          _roscoStatus: row.rosco_status || "Confirmed"
        };
      })
      .filter((row: any) => row._year === "2026");
  }, [rawDeliveryData]);

  // --- 🧠 STEP 2: EXTRACT DROPDOWN OPTIONS ---
  const { availableOffices, availableSports, availableMonths, availableDays } = useMemo(() => {
    const offices = Array.from(new Set(normalizedData.map(r => r._office))).filter(Boolean).sort();
    const sports = Array.from(new Set(normalizedData.map(r => r._sport))).filter(Boolean).sort();
    
    const monthMap = new Map();
    const dayMap = new Map();
    normalizedData.forEach(r => {
      if (r._monthYear !== "TBD") {
        if (!monthMap.has(r._monthYear) || r._sortableDay < monthMap.get(r._monthYear)) {
          monthMap.set(r._monthYear, r._sortableDay);
        }
      }
      if (r._sortableDay !== "0000-00-00") {
        dayMap.set(r._sortableDay, { label: r._exactDay, month: r._monthYear });
      }
    });
    return {
        availableOffices: offices,
        availableSports: sports,
        availableMonths: Array.from(monthMap.entries()).sort((a, b) => a[1].localeCompare(b[1])).map(e => e[0]),
        availableDays: Array.from(dayMap.entries()).sort((a, b) => a[0].localeCompare(b[0])).map(e => ({ val: e[0], label: e[1].label, month: e[1].month }))
    };
  }, [normalizedData]);

  // --- 🧠 STEP 3: WORKLOAD & REWORK ANALYSIS ---
  const workloadAnalysis = useMemo(() => {
      let data = normalizedData;
      
      if (workloadStartDate) data = data.filter(r => r._sortableDay >= workloadStartDate);
      if (workloadEndDate) data = data.filter(r => r._sortableDay <= workloadEndDate);

      let totalLines = 0, totalInScope = 0;
      let reworkTotalLines = 0, reworkInScope = 0, reworkOutScope = 0;
      const chartMap: Record<string, any> = {};

      data.forEach((row: any) => {
          totalLines += row._totalLines;
          totalInScope += row._inScopeLines;

          if (row._isRework) {
              reworkTotalLines += row._totalLines;
              reworkInScope += row._inScopeLines;
              reworkOutScope += row._outScopeLines;
          }

          const groupKey = workloadView === "MONTH" ? row._monthYear : row._sortableDay;
          const displayLabel = workloadView === "MONTH" ? row._monthYear : row._exactDay;

          if (groupKey !== "TBD" && groupKey !== "0000-00-00") {
              if (!chartMap[groupKey]) {
                  chartMap[groupKey] = { 
                      label: displayLabel, sortable: row._sortableDay, 
                      totalLines: 0, inScopeLines: 0, 
                      reworkTotal: 0, reworkInScope: 0, reworkOutScope: 0
                  };
              }
              chartMap[groupKey].totalLines += row._totalLines;
              chartMap[groupKey].inScopeLines += row._inScopeLines;
              
              if (row._isRework) {
                  chartMap[groupKey].reworkTotal += row._totalLines;
                  chartMap[groupKey].reworkInScope += row._inScopeLines;
                  chartMap[groupKey].reworkOutScope += row._outScopeLines;
              }
          }
      });

      const chartData = Object.values(chartMap).sort((a:any,b:any) => a.sortable.localeCompare(b.sortable)).map((m: any) => {
          return {
              ...m,
              inScopeReworkPct: m.reworkTotal > 0 ? Number(((m.reworkInScope / m.reworkTotal) * 100).toFixed(1)) : 0,
              outScopeReworkPct: m.reworkTotal > 0 ? Number(((m.reworkOutScope / m.reworkTotal) * 100).toFixed(1)) : 0,
          };
      });
      
      const inScopeReworkPct = reworkTotalLines > 0 ? ((reworkInScope / reworkTotalLines) * 100).toFixed(1) : "0";
      const outScopeReworkPct = reworkTotalLines > 0 ? ((reworkOutScope / reworkTotalLines) * 100).toFixed(1) : "0";

      return { chartData, totalLines, totalInScope, inScopeReworkPct, outScopeReworkPct };
  }, [normalizedData, workloadStartDate, workloadEndDate, workloadView]);

  // --- 🧠 STEP 4: GLOBAL DASHBOARD FILTERS & AGGREGATE ---
  const { 
    filteredData, kpis, monthlyTrends, dailyTrends, ftePerformance, pocRollup, reworkStats,
    reportTypes, regionalSportMatrix, assignmentReadiness, performanceTrends, topSavedProjects
  } = useMemo(() => {
    
    let finalData = normalizedData.filter((row: any) => {
      const s = searchTerm.toLowerCase();
      const matchesSearch = row._client.toLowerCase().includes(s) || 
                            row._fte.toLowerCase().includes(s) || 
                            row._poc.toLowerCase().includes(s) || 
                            row._id.toString().includes(s);
      
      const matchesStatus = filterStatus === "ALL" || 
                           (filterStatus === "ON_TIME" && row._delayDays <= 0) ||
                           (filterStatus === "DELAYED" && row._delayDays > 0) ||
                           (filterStatus === "REWORK" && row._isRework);

      const matchesOffice = selectedOffice === "ALL" || row._office === selectedOffice;
      const matchesSport = selectedSport === "ALL" || row._sport === selectedSport;
      const matchesMonth = selectedMonth === "ALL" || row._monthYear === selectedMonth;
      const matchesDay = selectedDay === "ALL" || row._sortableDay === selectedDay;

      return matchesSearch && matchesStatus && matchesOffice && matchesSport && matchesMonth && matchesDay;
    });

    let totalDelays = 0, sumDelayDays = 0, totalReworks = 0;
    let sumExpected = 0, sumActual = 0, validBurnExpected = 0, validBurnActual = 0;
    let totalDaysSaved = 0, totalMet = 0, totalMissed = 0;

    const monthlyMap: Record<string, any> = {};
    const dailyMap: Record<string, any> = {};
    const fteMap: Record<string, any> = {};
    const pocMap: Record<string, any> = {};
    const reportTypeMap: Record<string, number> = {};
    const regSportMap: Record<string, any> = {};
    const clientSavedMap: Record<string, number> = {};
    let assignedCount = 0, pendingCount = 0;

    finalData.forEach((row: any) => {
      if (row._delayDays > 0) { totalDelays++; sumDelayDays += row._delayDays; }
      if (row._isRework) totalReworks++;
      
      sumExpected += row._expectedEffort;
      sumActual += row._actualSpent;
      
      if (row._actualSpent > 0 || row._slaStatus !== "PENDING") {
          validBurnExpected += row._expectedEffort;
          validBurnActual += row._actualSpent;
      }
      
      totalDaysSaved += row._daysSaved;

      if (row._daysSaved > 0) {
          clientSavedMap[row._client] = (clientSavedMap[row._client] || 0) + row._daysSaved;
      }
      
      if (row._slaStatus === "MET") totalMet++;
      else if (row._slaStatus === "MISSED") totalMissed++;

      if (!monthlyMap[row._monthYear]) {
        monthlyMap[row._monthYear] = { 
          label: row._monthYear, sortable: row._sortableDay, volume: 0, 
          delayed: 0, delayDays: 0, met: 0, missed: 0, pending: 0, daysSaved: 0
        };
      }
      monthlyMap[row._monthYear].volume += 1;
      monthlyMap[row._monthYear].daysSaved += row._daysSaved;
      
      if (row._slaStatus === "MET") monthlyMap[row._monthYear].met += 1;
      else if (row._slaStatus === "MISSED") monthlyMap[row._monthYear].missed += 1;
      else monthlyMap[row._monthYear].pending += 1;
      
      if (!dailyMap[row._sortableDay]) dailyMap[row._sortableDay] = { label: row._exactDay, sortable: row._sortableDay, volume: 0, delayed: 0, delayDays: 0 };
      dailyMap[row._sortableDay].volume += 1;

      if (row._delayDays > 0) {
        monthlyMap[row._monthYear].delayed += 1;
        monthlyMap[row._monthYear].delayDays += row._delayDays;
        dailyMap[row._sortableDay].delayed += 1;
        dailyMap[row._sortableDay].delayDays += row._delayDays;
      }

      reportTypeMap[row._reportType] = (reportTypeMap[row._reportType] || 0) + 1;
      if (row._assignmentStatus.toLowerCase() === 'assigned') assignedCount++;
      if (row._assignmentStatus.toLowerCase() === 'pending') pendingCount++;

      if (!regSportMap[row._office]) regSportMap[row._office] = { office: row._office, total: 0 };
      regSportMap[row._office][row._sport] = (regSportMap[row._office][row._sport] || 0) + 1;
      regSportMap[row._office].total += 1;

      if (!fteMap[row._fte]) fteMap[row._fte] = { name: row._fte, total: 0, delayed: 0, delayDays: 0, reworks: 0, errorRate: [], expectedH: 0, actualH: 0 };
      fteMap[row._fte].total += 1;
      fteMap[row._fte].expectedH += row._expectedEffort;
      fteMap[row._fte].actualH += row._actualSpent;
      if (row._delayDays > 0) { fteMap[row._fte].delayed += 1; fteMap[row._fte].delayDays += row._delayDays; }
      if (row._isRework) fteMap[row._fte].reworks += 1;
      const err = Number(row['Error %']?.replace('%', '') || 0);
      if (err > 0) fteMap[row._fte].errorRate.push(err);

      if (!pocMap[row._poc]) pocMap[row._poc] = { name: row._poc, total: 0, delayed: 0, expectedH: 0, actualH: 0, ftes: new Set() };
      pocMap[row._poc].total += 1;
      pocMap[row._poc].expectedH += row._expectedEffort;
      pocMap[row._poc].actualH += row._actualSpent;
      pocMap[row._poc].ftes.add(row._fte); 
      if (row._delayDays > 0) pocMap[row._poc].delayed += 1;
    });

    const COLORS = ['#f43f5e', '#f97316', '#f59e0b', '#8b5cf6', '#64748b', '#0ea5e9', '#10b981'];

    const perfTrends = Object.values(monthlyMap).filter((m:any) => m.label !== "TBD").sort((a:any, b:any) => a.sortable.localeCompare(b.sortable))
      .map((m:any) => {
          const validMonthVol = m.met + m.missed; 
          return { 
              ...m, 
              avgDelay: m.delayed > 0 ? (m.delayDays / m.delayed).toFixed(1) : 0,
              slaRate: validMonthVol > 0 ? Number(((m.met / validMonthVol) * 100).toFixed(1)) : 0 
          };
      });

    const fteArray = Object.values(fteMap).map((f: any) => ({
        ...f,
        slaRate: f.total > 0 ? (((f.total - f.delayed) / f.total) * 100).toFixed(0) : 100,
        avgError: f.errorRate.length > 0 ? (f.errorRate.reduce((a:number,b:number)=>a+b,0) / f.errorRate.length).toFixed(1) : 0,
        avgDelay: f.delayed > 0 ? (f.delayDays / f.delayed).toFixed(1) : 0,
      })).sort((a: any, b: any) => b.total - a.total); 

    const pocArray = Object.values(pocMap).map((p: any) => ({
      ...p,
      teamSize: p.ftes.size,
      healthScore: p.total > 0 ? (((p.total - p.delayed) / p.total) * 100).toFixed(0) : 100,
      effortBurn: p.expectedH > 0 ? ((p.actualH / p.expectedH) * 100).toFixed(0) : 0
    })).sort((a: any, b: any) => b.total - a.total);

    const topSavedProjects = Object.entries(clientSavedMap)
      .map(([name, saved]) => ({ name: truncateText(name, 18), value: saved }))
      .sort((a, b) => (b.value as number) - (a.value as number))
      .slice(0, 6);
      
    return { 
      filteredData: finalData,
      kpis: { 
        total: finalData.length, delays: totalDelays, reworks: totalReworks,
        avgDelay: totalDelays > 0 ? (sumDelayDays / totalDelays).toFixed(1) : "0",
        effortBurn: validBurnExpected > 0 ? ((validBurnActual / validBurnExpected) * 100).toFixed(1) : "0",
        totalDaysSaved: totalDaysSaved,
        overallSla: (totalMet + totalMissed) > 0 ? ((totalMet / (totalMet + totalMissed)) * 100).toFixed(1) : "0"
      },
      performanceTrends: perfTrends,
      monthlyTrends: perfTrends.slice(-8), 
      dailyTrends: Object.values(dailyMap).filter((d:any) => d.sortable !== "0000-00-00").sort((a:any, b:any) => a.sortable.localeCompare(b.sortable)).map((d:any) => ({ ...d, avgDelay: d.delayed > 0 ? (d.delayDays / d.delayed).toFixed(1) : 0 })).slice(-30),
      ftePerformance: fteArray, 
      pocRollup: pocArray,
      reportTypes: Object.keys(reportTypeMap).map(k => ({ name: truncateText(k, 20), value: reportTypeMap[k] })).sort((a, b) => b.value - a.value).map((d, i) => ({ ...d, color: COLORS[i % COLORS.length] })), 
      regionalSportMatrix: Object.values(regSportMap).sort((a: any, b: any) => b.total - a.total).slice(0, 6), 
      assignmentReadiness: { assigned: assignedCount, pending: pendingCount },
      reworkStats: { expected: sumExpected.toFixed(0), actual: sumActual.toFixed(0) },
      topSavedProjects
    };
  }, [normalizedData, searchTerm, filterStatus, selectedMonth, selectedDay, selectedOffice, selectedSport]);



  // --- 🧠 STEP 5: ROSCO ID DEEP DIVE CALCULATIONS (ADDED DELAY & REWORK DATA) ---
  const roscoAnalysis = useMemo(() => {
    if (!roscoSearch.trim()) return null;
    const matchingRows = normalizedData.filter(r => r._id.toString().toLowerCase() === roscoSearch.trim().toLowerCase());
    
    if (matchingRows.length === 0) return { data: [], totalSpent: 0, avgSpent: 0, totalDelays: 0, totalReworks: 0, totalEarly: 0 };

    let totalSpent = 0, totalDelays = 0, totalReworks = 0, totalEarly = 0;
    const deliveryMap: Record<string, any> = {};

    matchingRows.forEach((row: any) => {
      const dId = row._deliveryId;
      if (!deliveryMap[dId]) {
        deliveryMap[dId] = { 
            deliveryId: dId, actualSpent: 0, expectedEffort: 0, count: 0,
            fte: row._fte, date: row.actual_delivered_date || row.original_delivery_date || row._exactDay, sortDate: row._sortableDay,
            delayDays: 0, daysSaved: 0, isRework: false, isActive: false 
        };
      }
      deliveryMap[dId].actualSpent += row._actualSpent;
      deliveryMap[dId].expectedEffort += row._expectedEffort;
      deliveryMap[dId].count += 1;
      
      if (row._actualSpent > 0 || row._slaStatus !== "PENDING") {
          deliveryMap[dId].isActive = true;
      }
      
      // Inherit the maximum delay, saved days, or rework status for this delivery
      deliveryMap[dId].delayDays = Math.max(deliveryMap[dId].delayDays, row._delayDays);
      deliveryMap[dId].daysSaved = Math.max(deliveryMap[dId].daysSaved, row._daysSaved);
      if (row._isRework) deliveryMap[dId].isRework = true;

      totalSpent += row._actualSpent;
    });

    const chartData = Object.values(deliveryMap).sort((a:any, b:any) => a.sortDate.localeCompare(b.sortDate));
    
    // Accurately count Delays, Early, and Reworks directly from the grouped Delivery IDs
    chartData.forEach(d => {
        if (d.delayDays > 0) totalDelays++;
        if (d.daysSaved > 0) totalEarly++;
        if (d.isRework) totalReworks++;
    });

    const activeDeliveries = chartData.filter((d: any) => d.isActive);
    const avgSpent = activeDeliveries.length > 0 ? totalSpent / activeDeliveries.length : 0;
    
    chartData.forEach(d => { d.avgActual = Number(avgSpent.toFixed(1)); });

    return { data: chartData, totalSpent, avgSpent, totalDelays, totalReworks, totalEarly };
  }, [normalizedData, roscoSearch]);

  const modalAnalytics = useMemo(() => {
    if (!selectedRecord) return null;
    const totalEvaluated = Number(selectedRecord.delivery_metrics?.Workload?.Total_Evaluated ?? selectedRecord['Total Lines'] ?? 0);
    const passedScope = Number(selectedRecord.delivery_metrics?.Workload?.Passed ?? selectedRecord['In Scope'] ?? 0);
    const failedScope = Number(selectedRecord.delivery_metrics?.Workload?.Failed ?? selectedRecord['Out Of Scope'] ?? 0);
    const errorRate = Number(selectedRecord.delivery_metrics?.Accuracy?.Failed ?? selectedRecord['Error %']?.replace('%','') ?? 0);

    const scopeDistribution = [
      { name: "In Scope", value: passedScope, color: "#10b981" },
      { name: "Out of Scope", value: failedScope, color: "#f43f5e" },
    ].filter(d => d.value > 0);

    const lifecycle = [
      { label: "Monitoring Started", date: selectedRecord['Monitoring Start Date'], icon: PlayCircle, color: "text-blue-500", bg: "bg-blue-100 dark:bg-blue-500/20" },
      { label: "Monitoring Ended", date: selectedRecord['Monitoring End Date'], icon: Activity, color: "text-indigo-500", bg: "bg-indigo-100 dark:bg-indigo-500/20" },
      { label: "Expected Target", date: selectedRecord['Best Expected Date'] || selectedRecord['Original Delivery Date'], icon: Target, color: "text-amber-500", bg: "bg-amber-100 dark:bg-amber-500/20" },
      selectedRecord._isRework ? { label: "Rework Initiated", date: selectedRecord['Rework Postponement Date'] || "Logged", icon: RefreshCw, color: "text-purple-500", bg: "bg-purple-100 dark:bg-purple-500/20" } : null,
      { label: "Final Sign-off", date: selectedRecord['Delivered Date'] || selectedRecord['Final Delivery Date'] || "Pending", icon: Flag, color: "text-emerald-500", bg: "bg-emerald-100 dark:bg-emerald-500/20", isFinal: true }
    ].filter(Boolean); 

    const delayText = selectedRecord._delayDays > 0 ? `faced a delay of ${selectedRecord._delayDays} days` : `was completed on-time`;
    const effortText = selectedRecord._actualSpent > selectedRecord._expectedEffort 
      ? `exceeded the planned allocation, taking ${selectedRecord._actualSpent} hours (vs ${selectedRecord._expectedEffort} expected)` 
      : `was delivered efficiently in ${selectedRecord._actualSpent} hours against an expected ${selectedRecord._expectedEffort} hours`;
    
    let reworkText = selectedRecord._isRework ? `The delivery required a rework cycle to address issues.` : `It bypassed any rework phases, achieving immediate sign-off.`;
    if(errorRate > 0) reworkText += ` The final review flagged an error rate of ${errorRate}%.`;

    const narrative = `This ${selectedRecord._reportType || 'report'} for ${selectedRecord._client} was managed under the purview of ${selectedRecord._poc} and executed operationally by ${selectedRecord._fte}. Monitoring spanned from ${selectedRecord['Monitoring Start Date'] || 'N/A'} to ${selectedRecord['Monitoring End Date'] || 'N/A'}. 
    
In terms of Service Level Agreements, the project ${delayText}. From an effort tracking standpoint, the task ${effortText}. The team evaluated a total workload of ${formatLargeNumber(totalEvaluated)} data lines. ${reworkText}`;

    return { scopeDistribution, totalLines: totalEvaluated, errorRate, lifecycle, narrative };
  }, [selectedRecord]);

  const totalPages = Math.ceil(filteredData.length / rowsPerPage);
  const currentTableData = useMemo(() => {
    const firstPageIndex = (currentPage - 1) * rowsPerPage;
    return filteredData.slice(firstPageIndex, firstPageIndex + rowsPerPage);
  }, [currentPage, filteredData]);

  React.useEffect(() => { setCurrentPage(1); }, [searchTerm, filterStatus, selectedMonth, selectedDay, selectedOffice, selectedSport]);

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-white dark:bg-[#111623] border border-slate-200 dark:border-slate-800 p-3 rounded-lg shadow-xl z-50">
          <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-1">{label || payload[0].name}</p>
          {payload.map((entry: any, index: number) => (
            <p key={index} className="text-xs font-black flex items-center justify-between gap-4" style={{ color: entry.color || '#3b82f6' }}>
              <span>{entry.name}</span>
              <span>{entry.value}{entry.name.includes("Rate") || entry.name.includes("%") ? "%" : ""}</span>
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  // --- 🧠 STEP 6: SCATTER PLOT CORRELATION ENGINE ---
  const scatterData = useMemo(() => {
    const projMap: Record<string, any> = {};
    
    filteredData.forEach((row: any) => {
      // Group by ROSCO ID to make each project a dot
      const pId = row._id;
      if (!projMap[pId]) {
        projMap[pId] = {
          roscoId: pId,
          client: row._client,
          totalLines: 0,
          expectedEffort: 0,
          actualSpent: 0,
          delayDays: 0,
          daysSaved: 0,
          reworks: 0,
          volume: 0
        };
      }
      projMap[pId].totalLines += row._totalLines;
      projMap[pId].expectedEffort += row._expectedEffort;
      projMap[pId].actualSpent += row._actualSpent;
      projMap[pId].delayDays += row._delayDays;
      projMap[pId].daysSaved += row._daysSaved;
      projMap[pId].volume += 1;
      if (row._isRework) projMap[pId].reworks += 1;
    });

    return Object.values(projMap);
  }, [filteredData]);

  if (isLoading) return <div className="flex items-center justify-center h-screen bg-[#F9FBFC] dark:bg-[#08090A]"><div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div></div>;
  if (isError) return <div className="flex items-center justify-center h-screen bg-[#F9FBFC] dark:bg-[#08090A] text-red-500 font-medium">Failed to load Delivery Analytics.</div>;

  

  return (
    <div className="min-h-screen bg-[#F9FBFC] dark:bg-[#08090A] p-4 lg:p-8 text-slate-900 dark:text-slate-100 transition-colors duration-300 relative flex flex-col gap-6 overflow-x-hidden">
      
      {/* MODAL */}
      {selectedRecord && modalAnalytics && (
        <div className="fixed inset-0 z-50 flex items-center justify-end bg-slate-900/60 backdrop-blur-sm p-4 sm:p-6 animate-in fade-in duration-300">
          <div className="absolute inset-0" onClick={() => setSelectedRecord(null)}></div>
          <div className="relative w-full max-w-5xl h-full max-h-[90vh] bg-white dark:bg-[#0B0F1A] border border-slate-200 dark:border-slate-800 rounded-3xl shadow-2xl flex flex-col overflow-hidden animate-in slide-in-from-right-8 duration-500">
            <div className="flex justify-between items-start p-6 border-b border-slate-100 dark:border-slate-800/60 bg-slate-50/50 dark:bg-white/[0.02] shrink-0">
              <div>
                <h2 className="text-xl font-black text-slate-800 dark:text-white flex items-center gap-2 mb-1"><BarChart3 className="text-blue-500" /> Project Dossier</h2>
                <div className="flex items-center gap-3 text-xs font-medium text-slate-500 dark:text-slate-400">
                  <span className="flex items-center gap-1"><Briefcase size={14}/> {selectedRecord._client}</span>
                  <span className="w-1 h-1 rounded-full bg-slate-300 dark:bg-slate-700"></span>
                  <span className="flex items-center gap-1"><Hash size={14}/> {selectedRecord._id}</span>
                </div>
              </div>
              <button onClick={() => setSelectedRecord(null)} className="p-2 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-500 rounded-full transition-all hover:rotate-90 hover:scale-110"><X size={18} /></button>
            </div>
            
            <div className="flex-1 overflow-y-auto p-6 lg:p-10 custom-scrollbar bg-slate-50/30 dark:bg-[#08090A]/50 flex flex-col gap-6">
              <div className="bg-blue-50/50 dark:bg-blue-500/5 border border-blue-100 dark:border-blue-500/20 rounded-xl p-5">
                <h3 className="text-xs font-black uppercase tracking-widest text-blue-600 dark:text-blue-400 mb-2 flex items-center gap-2">
                  <AlignLeft size={14} /> Executive Overview Walkthrough
                </h3>
                <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed font-medium">{modalAnalytics.narrative}</p>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <div className="p-4 bg-white dark:bg-[#111623] rounded-xl border border-slate-200 dark:border-slate-800/60 shadow-sm">
                  <span className="text-[10px] uppercase font-bold text-slate-400 mb-1 flex items-center">Delay Status</span>
                  <span className={`text-sm font-bold flex items-center gap-1 ${selectedRecord._delayDays > 0 ? "text-rose-500" : "text-emerald-500"}`}>
                    {selectedRecord._delayDays > 0 ? <AlertCircle size={14}/> : <CheckCircle2 size={14}/>} 
                    {selectedRecord._delayDays > 0 ? `${selectedRecord._delayDays} Days Late` : "On Time"}
                  </span>
                </div>
                <div className="p-4 bg-white dark:bg-[#111623] rounded-xl border border-slate-200 dark:border-slate-800/60 shadow-sm">
                  <span className="text-[10px] uppercase font-bold text-slate-400 mb-1 flex items-center">Rework Status</span>
                  <span className={`text-sm font-bold flex items-center gap-1 ${selectedRecord._isRework ? "text-purple-500" : "text-slate-500"}`}>
                    <RefreshCw size={14}/> {selectedRecord._isRework ? "Rework Done" : "No Rework"}
                  </span>
                </div>
                <div className="p-4 bg-white dark:bg-[#111623] rounded-xl border border-slate-200 dark:border-slate-800/60 shadow-sm">
                  <span className="text-[10px] uppercase font-bold text-slate-400 mb-1 flex items-center">Effort Burn</span>
                  <span className={`text-sm font-bold flex items-center gap-1 ${selectedRecord._actualSpent > selectedRecord._expectedEffort ? "text-rose-500" : "text-emerald-500"}`}>
                    <Zap size={14}/> {selectedRecord._actualSpent} / {selectedRecord._expectedEffort} h
                  </span>
                </div>
                <div className="p-4 bg-white dark:bg-[#111623] rounded-xl border border-slate-200 dark:border-slate-800/60 shadow-sm">
                  <span className="text-[10px] uppercase font-bold text-slate-400 mb-1 flex items-center">Data Error Rate</span>
                  <span className={`text-sm font-bold flex items-center gap-1 ${modalAnalytics.errorRate > 10 ? "text-amber-500" : "text-emerald-500"}`}>
                    <Target size={14}/> {modalAnalytics.errorRate}%
                  </span>
                </div>
              </div>

              <div className="bg-white dark:bg-[#111623] border border-slate-200 dark:border-slate-800/60 rounded-xl p-6 shadow-sm">
                <h3 className="text-xs font-black uppercase tracking-widest text-slate-400 mb-6 flex items-center gap-2">
                  <Clock size={14} className="text-blue-500"/> Project Lifecycle
                </h3>
                <div className="relative flex flex-col md:flex-row justify-between items-start md:items-center gap-6 md:gap-0">
                  <div className="hidden md:block absolute top-1/2 left-8 right-8 h-0.5 bg-slate-100 dark:bg-slate-800 -translate-y-1/2 z-0"></div>
                  {modalAnalytics.lifecycle.map((step: any, i: number) => (
                    <div key={i} className="relative z-10 flex md:flex-col items-center gap-4 md:gap-3 w-full md:w-auto text-left md:text-center group">
                      {i !== modalAnalytics.lifecycle.length - 1 && <div className="md:hidden absolute top-10 left-5 bottom-[-24px] w-0.5 bg-slate-100 dark:bg-slate-800 z-[-1]"></div>}
                      <div className={`h-10 w-10 rounded-full flex items-center justify-center border-4 border-white dark:border-[#111623] ${step.bg} ${step.color} shadow-sm group-hover:scale-110 transition-transform`}>
                        {React.createElement(step.icon, { size: 16 })}
                      </div>
                      <div>
                        <p className="text-[10px] font-black uppercase tracking-wider text-slate-500 mb-0.5">{step.label}</p>
                        <p className="text-sm font-bold text-slate-800 dark:text-slate-200">
                          {step.date ? step.date : <span className="text-slate-400 italic">Pending</span>}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className="bg-white dark:bg-[#111623] border border-slate-200 dark:border-slate-800/60 rounded-xl p-4 shadow-sm flex items-center relative h-56">
                  <div className="flex-1 h-full">
                    {modalAnalytics.scopeDistribution.length > 0 ? (
                      <ResponsiveContainer width="100%" height="100%">
                        <PieChart margin={{ right: 20 }}>
                          <Pie data={modalAnalytics.scopeDistribution} innerRadius={35} outerRadius={55} paddingAngle={2} dataKey="value" stroke="none">
                            {modalAnalytics.scopeDistribution.map((entry, index) => (<Cell key={`cell-${index}`} fill={entry.color} />))}
                          </Pie>
                          <RechartsTooltip content={<CustomTooltip />} />
                          <Legend verticalAlign="middle" align="right" layout="vertical" wrapperStyle={{ fontSize: '10px', fontWeight: 'bold' }} />
                        </PieChart>
                      </ResponsiveContainer>
                    ) : <div className="h-full w-full flex items-center justify-center text-xs text-slate-400 font-bold">No Scope Data</div>}
                  </div>
                  <h3 className="absolute top-4 left-4 text-[10px] font-black uppercase tracking-widest text-slate-400">Workload Scope ({formatLargeNumber(modalAnalytics.totalLines)} Lines)</h3>
                </div>
                
                <div className="bg-white dark:bg-[#111623] border border-slate-200 dark:border-slate-800/60 rounded-xl p-5 shadow-sm h-56 flex flex-col">
                  <h3 className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-4">Metadata</h3>
                  <div className="grid grid-cols-2 gap-y-6 gap-x-2 text-xs flex-1 content-center">
                    <div><span className="block text-[9px] font-bold text-slate-400 uppercase mb-0.5">FTE Assigned</span><span className="font-bold flex items-center gap-1"><User size={12} className="text-emerald-500"/> {selectedRecord._fte}</span></div>
                    <div><span className="block text-[9px] font-bold text-slate-400 uppercase mb-0.5">POC / Manager</span><span className="font-bold flex items-center gap-1"><ShieldCheck size={12} className="text-purple-500"/> {selectedRecord._poc}</span></div>
                    <div><span className="block text-[9px] font-bold text-slate-400 uppercase mb-0.5">Sport / Category</span><span className="font-bold flex items-center gap-1"><Trophy size={12} className="text-amber-500"/> {selectedRecord._sport}</span></div>
                    <div><span className="block text-[9px] font-bold text-slate-400 uppercase mb-0.5">Office Hub</span><span className="font-bold flex items-center gap-1"><Globe size={12} className="text-blue-500"/> {selectedRecord._office}</span></div>
                  </div>
                </div>
              </div>
            </div>

            <div className="p-4 border-t border-slate-100 dark:border-slate-800/60 bg-slate-50/50 dark:bg-white/[0.02] text-xs text-slate-400 flex items-center justify-between shrink-0">
              <span className="flex items-center gap-2"><FileText size={14}/> <strong>Raw Description:</strong> {selectedRecord.Description || selectedRecord.description_text || "No Description"}</span>
            </div>
          </div>
        </div>
      )}

      {/* HEADER & CONTROLS */}
      <div className="flex flex-col xl:flex-row justify-between items-start xl:items-center gap-4 bg-white dark:bg-[#111623] p-5 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
        <div>
          <h1 className="text-2xl font-black tracking-tight flex items-center gap-3">
            <ShieldCheck className="text-blue-500" size={28} /> GMS DashBoard
          </h1>
          <p className="text-xs text-slate-500 mt-1">Analyzing <span className="font-bold text-blue-500">2026 Deliveries</span> ({kpis.total} records).</p>
        </div>

        <div className="flex flex-wrap items-center gap-3 w-full xl:w-auto">
          <CustomDropdown 
            icon={CalendarDays}
            defaultLabel="All Months"
            value={selectedMonth}
            options={availableMonths}
            onChange={(val: string) => { setSelectedMonth(val); setSelectedDay("ALL"); }}
          />
          <CustomDropdown 
            icon={Clock}
            defaultLabel="All Days"
            value={selectedDay}
            options={availableDays.filter((d:any) => selectedMonth === "ALL" || d.month === selectedMonth)}
            onChange={(val: string) => setSelectedDay(val)}
          />
          <CustomDropdown 
            icon={Globe}
            defaultLabel="All Offices"
            value={selectedOffice}
            options={availableOffices}
            onChange={(val: string) => setSelectedOffice(val)}
          />
          <CustomDropdown 
            icon={Trophy}
            defaultLabel="All Sports"
            value={selectedSport}
            options={availableSports}
            onChange={(val: string) => setSelectedSport(val)}
          />

          <div className="flex bg-slate-100 dark:bg-[#0B0F1A] p-1 rounded-lg w-full sm:w-auto">
            {["ALL", "ON_TIME", "DELAYED", "REWORK"].map((status) => (
              <button 
                key={status} onClick={() => setFilterStatus(status as any)} 
                className={`flex-1 sm:flex-none px-3 py-1.5 text-[10px] font-black rounded-md transition-all ${filterStatus === status ? 'bg-white dark:bg-slate-800 shadow-sm text-blue-600 dark:text-blue-400' : 'text-slate-500 hover:text-slate-700'}`}
              >
                {status.replace('_', '-')}
              </button>
            ))}
          </div>

          <div className="relative w-full sm:w-64">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={14} />
            <input type="text" placeholder="Search Client, FTE..." value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} className="w-full bg-slate-50 dark:bg-[#0B0F1A] border border-slate-200 dark:border-slate-700 text-xs font-bold rounded-lg pl-9 pr-3 py-2 outline-none focus:border-blue-500 transition-colors" />
          </div>
        </div>
      </div>

      {/* KPI RIBBON */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { title: "Total Volume", value: kpis.total, icon: <Activity />, color: "text-blue-500" },
          { title: "SLA Met Rate", value: `${kpis.overallSla}%`, icon: <ShieldCheck />, color: "text-emerald-500", tooltip: "Percentage of items that met the Original Delivery Date." },
          { title: "Days Saved", value: `+${kpis.totalDaysSaved}d`, icon: <FastForward />, color: "text-indigo-500", tooltip: "Total cumulative days saved by delivering ahead of schedule." },
          // { title: "Avg Delay", value: `${kpis.avgDelay}d`, icon: <Clock />, color: "text-amber-500" },
          { title: "Effort Burn Rate", value: `${kpis.effortBurn}%`, icon: <Target />, color: Number(kpis.effortBurn) > 100 ? "text-rose-500" : "text-emerald-500" }
        ].map((kpi, idx) => (
          <div key={idx} className="bg-white dark:bg-[#111623] border border-slate-200 dark:border-slate-800/60 rounded-xl p-4 shadow-sm flex items-center justify-between group">
            <div>
              <span className="text-[10px] font-black uppercase tracking-widest text-slate-400 flex items-center mb-1">{kpi.title} {kpi.tooltip && <InfoTooltip text={kpi.tooltip} align="left" />}</span>
              <div className="text-xl font-black dark:text-white">{kpi.value}</div>
            </div>
            <div className={`p-2 rounded-lg bg-slate-50 dark:bg-slate-800/50 ${kpi.color}`}>{React.cloneElement(kpi.icon, { size: 18 })}</div>
          </div>
        ))}
      </div>
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 mt-2">

      {/* 1. SLA STACKED BAR CHART */}
        <div className="bg-white dark:bg-[#111623] border border-slate-200 dark:border-slate-800/60 rounded-xl p-5 shadow-sm h-80 flex flex-col">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xs font-black uppercase tracking-widest text-slate-400 flex items-center gap-2">
              <Target size={14} className="text-emerald-500"/> Monthly SLA Volume (Met vs Missed)
            </h3>
          </div>
          <div className="flex-1 w-full text-xs">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={performanceTrends} margin={{ top: 20, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.1} />
                <XAxis dataKey="label" axisLine={false} tickLine={false} />
                <YAxis axisLine={false} tickLine={false} />
                <RechartsTooltip content={<SlaTooltip />} cursor={{ fill: 'transparent' }} />
                <Legend wrapperStyle={{ fontSize: '10px', fontWeight: 'bold', paddingTop: '10px' }} />
                <Bar dataKey="met" name="Met Target" stackId="a" fill="#10b981" radius={[0, 0, 0, 0]} maxBarSize={50}><LabelList dataKey="met" position="inside" fill="#ffffff" fontSize={10} fontWeight="bold" formatter={(value: number) => value > 0 ? value : ""} /></Bar>
                <Bar dataKey="pending" name="Pending (Future)" stackId="a" fill="#94a3b8" radius={[0, 0, 0, 0]} maxBarSize={50}><LabelList dataKey="pending" position="inside" fill="#ffffff" fontSize={10} fontWeight="bold" formatter={(value: number) => value > 0 ? value : ""} /></Bar>
                <Bar dataKey="missed" name="Missed Target" stackId="a" fill="#f43f5e" radius={[4, 4, 0, 0]} maxBarSize={50}><LabelList dataKey="missed" position="inside" fill="#ffffff" fontSize={10} fontWeight="bold" formatter={(value: number) => value > 0 ? value : ""} /></Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* 2. DAYS SAVED COMBINED CARD (TREND VS LEADERBOARD TOGGLE) */}
        <div className="bg-white dark:bg-[#111623] border border-slate-200 dark:border-slate-800/60 rounded-xl p-5 shadow-sm h-80 flex flex-col">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-xs font-black uppercase tracking-widest text-slate-400 flex items-center gap-2">
              <FastForward size={14} className="text-indigo-500"/> Days Saved Analysis
            </h3>
            
            {/* THE TOGGLE BUTTONS */}
            <div className="flex items-center gap-1 bg-slate-100 dark:bg-slate-800/80 p-1 rounded-md">
              <button 
                onClick={() => setDaysSavedView("TREND")} 
                className={`px-2 py-1 text-[9px] font-black rounded transition-all ${daysSavedView === "TREND" ? "bg-white dark:bg-slate-700 shadow-sm text-indigo-500" : "text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"}`}
              >
                TREND
              </button>
              <button 
                onClick={() => setDaysSavedView("PROJECTS")} 
                className={`px-2 py-1 text-[9px] font-black rounded transition-all ${daysSavedView === "PROJECTS" ? "bg-white dark:bg-slate-700 shadow-sm text-indigo-500" : "text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"}`}
              >
                PROJECTS
              </button>
            </div>
          </div>

          <div className="flex-1 w-full text-xs">
            {daysSavedView === "TREND" ? (
              // --- VIEW 1: MONTHLY TREND ---
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={performanceTrends} margin={{ top: 20, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.1} />
                  <XAxis dataKey="label" axisLine={false} tickLine={false} />
                  <YAxis axisLine={false} tickLine={false} />
                  <RechartsTooltip content={<CustomTooltip />} cursor={{ fill: 'transparent' }} />
                  <Bar dataKey="daysSaved" name="Total Days Saved" fill="#6366f1" radius={[4, 4, 0, 0]} maxBarSize={50}>
                    <LabelList dataKey="daysSaved" position="top" fill="#6366f1" fontSize={10} fontWeight="bold" formatter={(v: number) => v > 0 ? `+${v}` : ""} />
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              // --- VIEW 2: TOP PROJECTS LEADERBOARD ---
              topSavedProjects.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart layout="vertical" data={topSavedProjects} margin={{ top: 0, right: 40, left: 10, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" horizontal={true} vertical={false} opacity={0.1} />
                    <XAxis type="number" hide />
                    <YAxis dataKey="name" type="category" axisLine={false} tickLine={false} tick={{ fill: '#64748b', fontSize: 10, fontWeight: 'bold' }} width={120} />
                    <RechartsTooltip content={<CustomTooltip />} cursor={{ fill: 'transparent' }} />
                    <Bar dataKey="value" name="Days Saved" fill="#8b5cf6" radius={[0, 4, 4, 0]} barSize={20}>
                      <LabelList dataKey="value" position="right" fill="#8b5cf6" fontSize={11} fontWeight="black" formatter={(v: number) => `+${v}d`} />
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full flex items-center justify-center text-xs text-slate-400 font-bold border border-dashed border-slate-200 dark:border-slate-800 rounded-xl">
                  No early deliveries recorded.
                </div>
              )
            )}
          </div>
        </div>

      </div>

      {/* ROSCO ID DEEP DIVE (WITH DELAYS & REWORK DATA) */}
      <div className="bg-white dark:bg-[#111623] border border-slate-200 dark:border-slate-800/60 rounded-xl p-5 shadow-sm flex flex-col">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-6 gap-4">
          <div>
            <h3 className="text-xs font-black uppercase tracking-widest text-slate-400 flex items-center gap-2">
              <Layers size={14} className="text-purple-500"/> ROSCO ID Effort Drill-Down
            </h3>
            <p className="text-[10px] text-slate-500 mt-1">Chronological performance of deliveries associated with a specific ROSCO ID.</p>
          </div>
          <div className="relative w-full md:w-72">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={14} />
            <input 
              type="text" 
              placeholder="Enter Exact ROSCO ID..." 
              value={roscoSearch} 
              onChange={(e) => setRoscoSearch(e.target.value)} 
              className="w-full bg-slate-50 dark:bg-[#0B0F1A] border border-slate-200 dark:border-slate-700 text-xs font-bold rounded-lg pl-9 pr-3 py-2 outline-none focus:border-purple-500 transition-colors" 
            />
          </div>
        </div>

        {roscoAnalysis ? (
          roscoAnalysis.data.length > 0 ? (
            <div className="flex flex-col xl:flex-row gap-6">
              <div className="flex flex-col gap-4 w-full xl:w-1/4">
                <div className="bg-slate-50 dark:bg-[#0B0F1A] p-4 rounded-xl border border-slate-100 dark:border-slate-800/60">
                  <p className="text-[10px] uppercase font-bold text-slate-500 mb-1">Total Actual Spent</p>
                  <p className="text-2xl font-black text-purple-500">{roscoAnalysis.totalSpent.toFixed(1)} hrs</p>
                </div>
                <div className="bg-slate-50 dark:bg-[#0B0F1A] p-4 rounded-xl border border-slate-100 dark:border-slate-800/60 flex items-center justify-between">
                  <div>
                    <p className="text-[10px] uppercase font-bold text-slate-500 mb-1">Avg Actual</p>
                    <p className="text-lg font-black text-amber-500">{roscoAnalysis.avgSpent.toFixed(1)} hrs</p>
                  </div>
                  <div className="text-right">
                    <p className="text-[10px] uppercase font-bold text-slate-500 mb-1">Deliveries</p>
                    <p className="text-lg font-black text-slate-800 dark:text-white">{roscoAnalysis.data.length}</p>
                  </div>
                </div>
                {/* 👇 THIS IS THE UPDATED CARD 👇 */}
                <div className="bg-slate-50 dark:bg-[#0B0F1A] p-4 rounded-xl border border-slate-100 dark:border-slate-800/60 flex items-center justify-between">
                  <div>
                    <p className="text-[10px] uppercase font-bold text-slate-500 mb-1">Delays</p>
                    <p className="text-lg font-black text-rose-500">{roscoAnalysis.totalDelays}</p>
                  </div>
                  <div className="text-center">
                    <p className="text-[10px] uppercase font-bold text-slate-500 mb-1">Early</p>
                    <p className="text-lg font-black text-indigo-500">{roscoAnalysis.totalEarly}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-[10px] uppercase font-bold text-slate-500 mb-1">Reworks</p>
                    <p className="text-lg font-black text-amber-500">{roscoAnalysis.totalReworks}</p>
                  </div>
                </div>
              </div>
              <div className="flex-1 h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={roscoAnalysis.data} margin={{ top: 25, right: 10, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.1} />
                    <XAxis dataKey="deliveryId" axisLine={false} tickLine={false} tick={{fontSize: 10}} />
                    
                    <YAxis yAxisId="left" axisLine={false} tickLine={false} tick={{fontSize: 10}} />
                    <YAxis yAxisId="right" orientation="right" axisLine={false} tickLine={false} tick={{fontSize: 10}} />
                    
                    <RechartsTooltip content={<RoscoTooltip />} cursor={{ fill: 'transparent' }} />
                    <Legend wrapperStyle={{ fontSize: '10px', fontWeight: 'bold' }} />
                    
                    <Bar yAxisId="left" dataKey="expectedEffort" name="Expected Effort (hrs)" fill="#94a3b8" radius={[4, 4, 0, 0]} maxBarSize={40} />
                    <Bar yAxisId="left" dataKey="actualSpent" name="Actual Spent (hrs)" fill="#a855f7" radius={[4, 4, 0, 0]} maxBarSize={40}>
                      <LabelList dataKey="actualSpent" position="top" fill="#a855f7" fontSize={10} fontWeight="bold" formatter={(val: number) => val > 0 ? val : ""} />
                    </Bar>
                    
                    <Line yAxisId="left" type="monotone" dataKey="avgActual" name="Avg Actual Spent" stroke="#f59e0b" strokeDasharray="5 5" strokeWidth={2} dot={false} />
                    <Line yAxisId="right" type="monotone" dataKey="delayDays" name="Delay (Days)" stroke="#ef4444" strokeWidth={2} dot={{ r: 3, fill: "#ef4444" }} />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </div>
          ) : (
            <div className="h-40 flex items-center justify-center text-xs font-bold text-slate-400 bg-slate-50 dark:bg-[#0B0F1A] rounded-xl border border-dashed border-slate-200 dark:border-slate-800">
              No deliveries found for ROSCO ID: &quot;{roscoSearch}&quot;
            </div>
          )
        ) : (
          <div className="h-40 flex items-center justify-center text-xs font-bold text-slate-400 bg-slate-50 dark:bg-[#0B0F1A] rounded-xl border border-dashed border-slate-200 dark:border-slate-800">
            Enter a ROSCO ID above to reveal chronological effort & delay breakdown.
          </div>
        )}
      </div>

      {/* WORKLOAD & REWORK ERROR ANALYSIS */}
      <div className="bg-white dark:bg-[#111623] border border-slate-200 dark:border-slate-800/60 rounded-xl p-5 shadow-sm flex flex-col mt-2">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-6 gap-4 border-b border-slate-100 dark:border-slate-800/60 pb-4">
          <div>
            <h3 className="text-xs font-black uppercase tracking-widest text-slate-400 flex items-center gap-2">
              <Scale size={14} className="text-blue-500"/> Workload Error Scoping
            </h3>
            <p className="text-[10px] text-slate-500 mt-1">Compare total lines against lines failed due to errors (In Scope). </p>
          </div>
          
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-1 bg-slate-100 dark:bg-slate-800/80 p-1 rounded-md">
              <button onClick={() => setWorkloadView("MONTH")} className={`px-2 py-1 text-[9px] font-black rounded transition-all ${workloadView === "MONTH" ? "bg-white dark:bg-slate-700 shadow-sm text-blue-500" : "text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"}`}>MONTHLY</button>
              <button onClick={() => setWorkloadView("DAY")} className={`px-2 py-1 text-[9px] font-black rounded transition-all ${workloadView === "DAY" ? "bg-white dark:bg-slate-700 shadow-sm text-blue-500" : "text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"}`}>DAILY</button>
            </div>

            <div className="flex items-center gap-2 bg-slate-50 dark:bg-[#0B0F1A] border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-1.5">
              <span className="text-[10px] font-bold text-slate-400 uppercase">From</span>
              <input 
                type="date" 
                value={workloadStartDate} 
                onChange={(e) => setWorkloadStartDate(e.target.value)} 
                className="bg-white dark:bg-[#111623] text-slate-900 dark:text-slate-100 text-xs font-bold outline-none cursor-pointer p-1 rounded border border-slate-200 dark:border-slate-700 w-full sm:w-[120px]"
              />
            </div>
            <div className="flex items-center gap-2 bg-slate-50 dark:bg-[#0B0F1A] border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-1.5">
              <span className="text-[10px] font-bold text-slate-400 uppercase">To</span>
              <input 
                type="date" 
                value={workloadEndDate} 
                onChange={(e) => setWorkloadEndDate(e.target.value)} 
                className="bg-white dark:bg-[#111623] text-slate-900 dark:text-slate-100 text-xs font-bold outline-none cursor-pointer p-1 rounded border border-slate-200 dark:border-slate-700 w-full sm:w-[120px]"
              />
            </div>
            {(workloadStartDate || workloadEndDate) && (
              <button 
                onClick={() => { setWorkloadStartDate(""); setWorkloadEndDate(""); }}
                className="text-[10px] font-bold text-rose-500 hover:text-rose-600 transition-colors uppercase tracking-wider"
              >
                Clear
              </button>
            )}
          </div>
        </div>

        <div className="flex flex-col xl:flex-row gap-6">
          <div className="flex flex-col gap-4 w-full xl:w-1/5">
             <div className="bg-slate-50 dark:bg-[#0B0F1A] p-4 rounded-xl border border-slate-100 dark:border-slate-800/60 flex items-center justify-between">
                <div>
                  <p className="text-[10px] uppercase font-bold text-slate-500 mb-1">Total Evaluated</p>
                  <p className="text-xl font-black text-blue-500">{formatLargeNumber(workloadAnalysis.totalLines)} lines</p>
                </div>
             </div>
             <div className="bg-slate-50 dark:bg-[#0B0F1A] p-4 rounded-xl border border-slate-100 dark:border-slate-800/60 flex items-center justify-between">
                <div>
                  <p className="text-[10px] uppercase font-bold text-slate-500 mb-1">Total In-Scope Error</p>
                  <p className="text-xl font-black text-rose-500">{formatLargeNumber(workloadAnalysis.totalInScope)} lines</p>
                </div>
             </div>
             <div className="bg-slate-50 dark:bg-[#0B0F1A] p-4 rounded-xl border border-slate-100 dark:border-slate-800/60 flex items-center justify-between">
                <div>
                  <p className="text-[10px] uppercase font-bold text-slate-500 mb-1">Rework: In-Scope</p>
                  <p className="text-lg font-black text-emerald-500">{workloadAnalysis.inScopeReworkPct}%</p>
                </div>
                <div className="text-right">
                  <p className="text-[10px] uppercase font-bold text-slate-500 mb-1">Out-of-Scope</p>
                  <p className="text-lg font-black text-slate-800 dark:text-white">{workloadAnalysis.outScopeReworkPct}%</p>
                </div>
             </div>
          </div>
          
          <div className="flex-1 h-72">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={workloadAnalysis.chartData} margin={{ top: 25, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.1} />
                <XAxis dataKey="label" axisLine={false} tickLine={false} tick={{fontSize: 10}} />
                <YAxis yAxisId="left" axisLine={false} tickLine={false} tick={{fontSize: 10}} tickFormatter={(v) => formatLargeNumber(v)} />
                <YAxis yAxisId="right" orientation="right" axisLine={false} tickLine={false} tick={{fontSize: 10}} tickFormatter={(v) => `${v}%`} />
                <RechartsTooltip content={<WorkloadTooltip />} cursor={{ fill: 'transparent' }} />
                <Legend wrapperStyle={{ fontSize: '10px', fontWeight: 'bold' }} />
                
                <Bar yAxisId="left" dataKey="totalLines" name="Total Evaluated" fill="#3b82f6" opacity={0.3} radius={[4, 4, 0, 0]} maxBarSize={50}>
                  <LabelList dataKey="totalLines" position="top" fill="#3b82f6" fontSize={10} fontWeight="bold" formatter={(v: number) => v > 0 ? formatLargeNumber(v) : ""} />
                </Bar>
                <Bar yAxisId="left" dataKey="inScopeLines" name="In Scope Error Lines" fill="#f43f5e" radius={[4, 4, 0, 0]} maxBarSize={50} />
                
                <Line yAxisId="right" type="monotone" dataKey="inScopeReworkPct" name="Rework: In-Scope %" stroke="#10b981" strokeWidth={3} dot={{ r: 4 }} />
                <Line yAxisId="right" type="monotone" dataKey="outScopeReworkPct" name="Rework: Out-of-Scope %" stroke="#a855f7" strokeWidth={3} dot={{ r: 4 }} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* MONTHLY SLA & EFFICIENCY TRENDS */}
      {/* MONTHLY SLA & EFFICIENCY TRENDS */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 mt-2">
        
        

      </div>

      {/* CROSS-FUNCTIONAL INSIGHTS ROW */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className="xl:col-span-2 bg-white dark:bg-[#111623] border border-slate-200 dark:border-slate-800/60 rounded-xl p-5 shadow-sm flex flex-col h-80">
          <h3 className="text-xs font-black uppercase tracking-widest text-slate-400 mb-4 flex items-center gap-2"><Network size={14} className="text-blue-500"/> Regional Sport Matrix (Cross-Functional)</h3>
          <div className="flex-1 w-full text-xs">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={regionalSportMatrix} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#334155" opacity={0.1} />
                <XAxis dataKey="office" axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: '#64748b' }} dy={10} />
                <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: '#64748b' }} />
                <RechartsTooltip content={<CustomTooltip />} />
                <Legend wrapperStyle={{ fontSize: '9px', fontWeight: 'bold' }} />
                {availableSports.slice(0, 6).map((sport: any, i: number) => (
                  <Bar key={sport} dataKey={sport} stackId="a" fill={['#3b82f6', '#f97316', '#10b981', '#8b5cf6', '#f43f5e', '#f59e0b'][i]} radius={i === availableSports.length-1 ? [4,4,0,0] : [0,0,0,0]} />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-white dark:bg-[#111623] border border-slate-200 dark:border-slate-800/60 rounded-xl p-5 shadow-sm flex flex-col h-80">
          <h3 className="text-xs font-black uppercase tracking-widest text-slate-400 mb-2 flex items-center gap-2"><FileBarChart size={14} className="text-purple-500"/> Delivery Format Demand</h3>
          {reportTypes.length > 0 ? (
            <div className="flex-1 flex flex-col">
              <div className="flex-1 min-h-[120px]">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={reportTypes} cx="50%" cy="50%" innerRadius={35} outerRadius={60} paddingAngle={2} dataKey="value" stroke="none">
                      {reportTypes.map((entry, index) => <Cell key={`cell-${index}`} fill={entry.color} />)}
                    </Pie>
                    <RechartsTooltip content={<CustomTooltip />} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="border-t border-slate-100 dark:border-slate-800 pt-3 mt-2">
                <p className="text-[10px] font-black uppercase text-slate-400 mb-2">Assignment Pipeline Readiness</p>
                <div className="flex gap-4">
                  <div className="flex-1 bg-slate-50 dark:bg-slate-800/50 p-2 rounded-lg">
                    <p className="text-[9px] text-slate-500 font-bold">Assigned</p>
                    <p className="text-lg font-black text-emerald-500">{assignmentReadiness.assigned}</p>
                  </div>
                  <div className="flex-1 bg-slate-50 dark:bg-slate-800/50 p-2 rounded-lg">
                    <p className="text-[9px] text-slate-500 font-bold">Pending</p>
                    <p className="text-lg font-black text-amber-500">{assignmentReadiness.pending}</p>
                  </div>
                </div>
              </div>
            </div>
          ) : <div className="flex-1 flex items-center justify-center text-xs font-medium text-slate-400">No report type data.</div>}
        </div>
      </div>

      {/* TRENDS & EFFORT */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-white dark:bg-[#111623] border border-slate-200 dark:border-slate-800/60 rounded-xl p-5 shadow-sm flex flex-col h-80">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-xs font-black uppercase tracking-widest text-slate-400 flex items-center gap-2">
              <TrendingUp size={14} className="text-blue-500"/> Volume vs Delay Trend
            </h3>
            <div className="flex items-center gap-1 bg-slate-100 dark:bg-slate-800/80 p-1 rounded-md">
              <button onClick={() => setTrendView("MONTH")} className={`px-2 py-1 text-[9px] font-black rounded transition-all ${trendView === "MONTH" ? "bg-white dark:bg-slate-700 shadow-sm text-blue-500" : "text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"}`}>MONTHLY</button>
              <button onClick={() => setTrendView("DAY")} className={`px-2 py-1 text-[9px] font-black rounded transition-all ${trendView === "DAY" ? "bg-white dark:bg-slate-700 shadow-sm text-blue-500" : "text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"}`}>DAILY</button>
            </div>
          </div>
          <div className="flex-1 w-full text-xs">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={trendView === "MONTH" ? monthlyTrends : dailyTrends} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#334155" opacity={0.1} />
                <XAxis dataKey="label" axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: '#64748b' }} dy={10} />
                <YAxis yAxisId="left" axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: '#64748b' }} />
                <YAxis yAxisId="right" orientation="right" axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: '#f43f5e' }} />
                <RechartsTooltip content={<CustomTooltip />} />
                <Bar yAxisId="left" dataKey="volume" name="Total Deliveries" fill="#3b82f6" radius={[4, 4, 0, 0]} barSize={trendView === "DAY" ? 10 : 20} opacity={0.8} />
                <Bar yAxisId="left" dataKey="delayed" name="Delayed Volume" fill="#f59e0b" radius={[4, 4, 0, 0]} barSize={trendView === "DAY" ? 10 : 20} />
                <Line yAxisId="right" type="monotone" dataKey="avgDelay" name="Avg Delay (Days)" stroke="#f43f5e" strokeWidth={3} dot={{ r: trendView === "DAY" ? 2 : 4, strokeWidth: 2 }} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-white dark:bg-[#111623] border border-slate-200 dark:border-slate-800/60 rounded-xl p-5 shadow-sm flex flex-col h-80">
          <h3 className="text-xs font-black uppercase tracking-widest text-slate-400 mb-4 flex items-center gap-2"><Clock size={14} className="text-blue-500"/> Global Effort Tracking</h3>
          <div className="flex-1 flex flex-col justify-center gap-8">
            <div>
              <div className="flex justify-between text-xs font-black mb-2">
                <span className="text-slate-500">Expected Effort</span>
                <span className="text-slate-800 dark:text-white">{reworkStats.expected} hrs</span>
              </div>
              <div className="h-4 w-full bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden"><div className="h-full bg-blue-500 w-full"></div></div>
            </div>
            <div>
              <div className="flex justify-between text-xs font-black mb-2">
                <span className="text-slate-500">Actual Spent</span>
                <span className={Number(kpis.effortBurn) > 100 ? "text-rose-500" : "text-emerald-500"}>{reworkStats.actual} hrs ({kpis.effortBurn}%)</span>
              </div>
              <div className="h-4 w-full bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden flex">
                <div className={`h-full ${Number(kpis.effortBurn) > 100 ? 'bg-rose-500' : 'bg-emerald-500'}`} style={{ width: `${Math.min(Number(kpis.effortBurn), 100)}%` }}></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ADVANCED CORRELATION ANALYSIS (SCATTER PLOT) */}
      <div className="bg-white dark:bg-[#111623] border border-slate-200 dark:border-slate-800/60 rounded-xl p-5 shadow-sm flex flex-col mt-2 h-[450px]">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-6 gap-4 border-b border-slate-100 dark:border-slate-800/60 pb-4">
          <div>
            <h3 className="text-xs font-black uppercase tracking-widest text-slate-400 flex items-center gap-2">
              <Activity size={14} className="text-purple-500"/> Project Outlier Matrix
            </h3>
            <p className="text-[10px] text-slate-500 mt-1">Discover correlations and spot outliers by plotting projects across dynamic metrics.</p>
          </div>
          
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">X-Axis:</span>
              <CustomDropdown 
                defaultLabel="Select Metric"
                value={scatterX}
                options={SCATTER_METRICS}
                onChange={(val: string) => setScatterX(val)}
              />
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Y-Axis:</span>
              <CustomDropdown 
                defaultLabel="Select Metric"
                value={scatterY}
                options={SCATTER_METRICS}
                onChange={(val: string) => setScatterY(val)}
              />
            </div>
          </div>
        </div>

        <div className="flex-1 w-full">
          {scatterData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart margin={{ top: 10, right: 20, bottom: 10, left: -10 }}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.1} />
                
                {/* Dynamically assign X and Y based on user selection */}
                <XAxis 
                  type="number" 
                  dataKey={scatterX} 
                  name={SCATTER_METRICS.find(m => m.val === scatterX)?.label} 
                  axisLine={false} 
                  tickLine={false} 
                  tick={{fontSize: 10, fill: '#64748b'}} 
                  tickFormatter={(v) => scatterX === 'totalLines' ? formatLargeNumber(v) : v}
                />
                
                <YAxis 
                  type="number" 
                  dataKey={scatterY} 
                  name={SCATTER_METRICS.find(m => m.val === scatterY)?.label} 
                  axisLine={false} 
                  tickLine={false} 
                  tick={{fontSize: 10, fill: '#64748b'}} 
                  tickFormatter={(v) => scatterY === 'totalLines' ? formatLargeNumber(v) : v}
                />
                
                {/* ZAxis determines bubble size based on volume of deliveries in that project */}
                <ZAxis type="number" dataKey="volume" range={[60, 400]} />
                
                <RechartsTooltip cursor={{ strokeDasharray: '3 3' }} content={<ScatterTooltip />} />
                
                <Scatter data={scatterData} fill="#8b5cf6" opacity={0.6}>
                  {scatterData.map((entry: any, index: number) => (
                    <Cell key={`cell-${index}`} fill={entry.delayDays > 0 ? "#f43f5e" : (entry.actualSpent > entry.expectedEffort ? "#f59e0b" : "#8b5cf6")} />
                  ))}
                </Scatter>
              </ScatterChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-full flex items-center justify-center text-xs font-bold text-slate-400 border border-dashed border-slate-200 dark:border-slate-800 rounded-xl">
              No project data available to plot.
            </div>
          )}
        </div>
      </div>

      {/* MATRIX ROW */}
      {/* <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="lg:col-span-2 bg-white dark:bg-[#111623] border border-slate-200 dark:border-slate-800/60 rounded-xl shadow-sm flex flex-col h-[400px]">
          <div className="p-4 border-b border-slate-100 dark:border-slate-800/60 flex justify-between items-center">
            <h3 className="text-xs font-black uppercase tracking-widest text-slate-400 flex items-center gap-2"><User size={14} className="text-emerald-500"/> Advanced FTE Matrix</h3>
          </div>
          <div className="overflow-y-auto custom-scrollbar">
            <table className="w-full text-left">
              <thead className="sticky top-0 bg-slate-50 dark:bg-[#0B0F1A] text-[9px] uppercase tracking-widest text-slate-400 border-b border-slate-200 dark:border-slate-800 z-10">
                <tr>
                  <th className="px-4 py-3 font-black">FTE Name</th>
                  <th className="px-4 py-3 font-black text-right">Volume</th>
                  <th className="px-4 py-3 font-black text-right">SLA %</th>
                  <th className="px-4 py-3 font-black text-right">Avg Delay</th>
                  <th className="px-4 py-3 font-black text-right">Avg Error %</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800/40">
                {ftePerformance.map((fte: any, i: number) => (
                  <tr key={i} className="hover:bg-slate-50 dark:hover:bg-slate-800/30">
                    <td className="px-4 py-2 text-xs font-bold dark:text-slate-200">{fte.name}</td>
                    <td className="px-4 py-2 text-xs font-medium text-right text-slate-500">{fte.total}</td>
                    <td className="px-4 py-2 text-xs font-bold text-right"><span className={Number(fte.slaRate) < 90 ? "text-amber-500" : "text-emerald-500"}>{fte.slaRate}%</span></td>
                    <td className="px-4 py-2 text-xs font-bold text-right"><span className={Number(fte.avgDelay) > 0 ? "text-rose-500" : "text-slate-500"}>{fte.avgDelay}d</span></td>
                    <td className="px-4 py-2 text-xs font-bold text-right"><span className={Number(fte.avgError) > 5 ? "text-rose-500" : "text-slate-500"}>{fte.avgError}%</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="lg:col-span-2 bg-white dark:bg-[#111623] border border-slate-200 dark:border-slate-800/60 rounded-xl shadow-sm flex flex-col h-[400px]">
          <div className="p-4 border-b border-slate-100 dark:border-slate-800/60 flex justify-between items-center">
            <h3 className="text-xs font-black uppercase tracking-widest text-slate-400 flex items-center gap-2"><Briefcase size={14} className="text-purple-500"/> Manager (POC) Portfolio Health</h3>
          </div>
          <div className="overflow-y-auto custom-scrollbar">
            <table className="w-full text-left">
              <thead className="sticky top-0 bg-slate-50 dark:bg-[#0B0F1A] text-[9px] uppercase tracking-widest text-slate-400 border-b border-slate-200 dark:border-slate-800 z-10">
                <tr>
                  <th className="px-4 py-3 font-black">Manager / POC</th>
                  <th className="px-4 py-3 font-black text-right">Portfolio Vol</th>
                  <th className="px-4 py-3 font-black text-right">Team Size</th>
                  <th className="px-4 py-3 font-black text-right">Health %</th>
                  <th className="px-4 py-3 font-black text-right">Effort Burn %</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800/40">
                {pocRollup.map((poc: any, i: number) => (
                  <tr key={i} className="hover:bg-slate-50 dark:hover:bg-slate-800/30">
                    <td className="px-4 py-2 text-xs font-bold dark:text-slate-200">{poc.name}</td>
                    <td className="px-4 py-2 text-xs font-medium text-right text-slate-500">{poc.total}</td>
                    <td className="px-4 py-2 text-xs font-medium text-right text-slate-500">{poc.teamSize} FTEs</td>
                    <td className="px-4 py-2 text-xs font-bold text-right"><span className={Number(poc.healthScore) < 90 ? "text-amber-500" : "text-emerald-500"}>{poc.healthScore}%</span></td>
                    <td className="px-4 py-2 text-xs font-bold text-right"><span className={Number(poc.effortBurn) > 100 ? "text-rose-500" : "text-emerald-500"}>{poc.effortBurn}%</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div> */}

      {/* MASTER DATA TABLE */}
      <div className="bg-white dark:bg-[#111623] border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm overflow-hidden flex flex-col mt-2">
        <div className="p-4 border-b border-slate-100 dark:border-slate-800/60 flex justify-between items-center bg-slate-50/50 dark:bg-[#0B0F1A]/50">
          <h3 className="text-sm font-black flex items-center gap-2"><FileText size={16} className="text-slate-400"/> Operational Master Log</h3>
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">{filteredData.length} records found</span>
        </div>
        
        <div className="overflow-x-auto custom-scrollbar max-h-[500px]">
          <table className="w-full text-left border-collapse min-w-[1000px]">
            <thead className="sticky top-0 bg-slate-50 dark:bg-[#0B0F1A] z-10 border-b border-slate-200 dark:border-slate-800/60 shadow-sm">
              <tr className="text-[9px] uppercase tracking-widest text-slate-400">
                <th className="px-4 py-3 font-black">ID</th>
                <th className="px-4 py-3 font-black">Client & Project</th>
                <th className="px-4 py-3 font-black">Office / POC</th>
                <th className="px-4 py-3 font-black">Orig Date</th>
                <th className="px-4 py-3 font-black">Delivered</th>
                <th className="px-4 py-3 font-black">SLA Target</th>
                <th className="px-4 py-3 font-black">Rosco Status</th>
                <th className="px-4 py-3 font-black">Days Saved</th>
                <th className="px-4 py-3 font-black text-right">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800/40">
              {currentTableData.length === 0 ? (
                <tr><td colSpan={9} className="px-5 py-10 text-center text-slate-400 text-xs font-medium">No records match current filters.</td></tr>
              ) : (
                currentTableData.map((row: any, idx: number) => (
                  <tr key={idx} onClick={() => setSelectedRecord(row)} className="hover:bg-slate-50 dark:hover:bg-white/[0.02] transition-colors cursor-pointer group">
                    <td className="px-4 py-3 text-xs font-bold text-slate-500">#{row._id}</td>
                    <td className="px-4 py-3">
                      <p className="text-xs font-bold dark:text-slate-200 truncate max-w-[200px]" title={row._client}>{row._client}</p>
                    </td>
                    <td className="px-4 py-3">
                       <p className="text-[10px] text-slate-500 flex items-center gap-1 font-bold"><Globe size={10}/> {row._office}</p>
                       <p className="text-[10px] text-slate-500 flex items-center gap-1 mt-0.5"><ShieldCheck size={10}/> {row._poc}</p>
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-500">{row.original_delivery_date || "N/A"}</td>
                    <td className="px-4 py-3 text-xs text-slate-500">{row.actual_delivered_date || "N/A"}</td>
                    <td className="px-4 py-3">
                      <div className="flex flex-col gap-1 items-start">
                        {row._slaStatus === "MET" ? (
                          <span className="text-[10px] font-bold text-emerald-500 flex items-center gap-1"><CheckCircle2 size={12}/> Met</span>
                        ) : row._slaStatus === "PENDING" ? (
                          <span className="text-[10px] font-bold text-slate-400 flex items-center gap-1"><Clock size={12}/> Pending</span>
                        ) : (
                          <span className="text-[10px] font-bold text-rose-500 flex items-center gap-1"><AlertTriangle size={12}/> Missed</span>
                        )}
                        {row._isRework && <span className="text-[9px] font-bold text-purple-500 bg-purple-50 dark:bg-purple-500/10 px-1.5 py-0.5 rounded">Rework</span>}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-[9px] font-black px-2 py-0.5 rounded bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300 flex items-center gap-1 w-fit">
                        <CheckCircle2 size={10} className="text-emerald-500"/> {row._roscoStatus}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`text-xs font-black ${row._daysSaved > 0 ? "text-indigo-500" : "text-slate-400"}`}>
                        {row._daysSaved > 0 ? `+${row._daysSaved}d` : "-"}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                       <button className="p-1.5 text-slate-400 group-hover:text-blue-500 group-hover:bg-blue-50 dark:group-hover:bg-blue-500/10 rounded-md transition-all group-hover:translate-x-1 inline-flex"><ChevronRight size={16} /></button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* PAGINATION CONTROLS */}
        {totalPages > 1 && (
          <div className="p-3 border-t border-slate-100 dark:border-slate-800/60 bg-slate-50/50 dark:bg-white/[0.02] flex items-center justify-between">
             <span className="text-xs text-slate-500 font-medium">Page {currentPage} of {totalPages}</span>
             <div className="flex gap-2">
               <button 
                 onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                 disabled={currentPage === 1}
                 className="p-1.5 rounded bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 disabled:opacity-50 text-slate-600 hover:bg-slate-100 transition-colors"
               ><ChevronLeft size={16} /></button>
               <button 
                 onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                 disabled={currentPage === totalPages}
                 className="p-1.5 rounded bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 disabled:opacity-50 text-slate-600 hover:bg-slate-100 transition-colors"
               ><ChevronRightIcon size={16} /></button>
             </div>
          </div>
        )}
      </div>

    </div>
  );
};

export default DeliveryDashboard;