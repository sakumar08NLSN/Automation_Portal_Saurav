"use client";

import { useState } from "react";
import { UploadCloud, Loader, Download } from "lucide-react";
import {
  useRunMmBsaQcMutation,
  useLazyDownloadFixtureTemplateQuery,
} from "@/state/api";

const QC_CHECKS = [
  { id: "duplicate_aid_final", title: "Duplicate AID Check" },
  { id: "audience_spotprice_check", title: "Audience & Spot Price Check" },
  { id: "program_category_check_mm", title: "Program Category Check" },
  { id: "channel_country_mapping_check", title: "Channel & Country Mapping" },
  { id: "apt_bt_check", title: "APT / BT Check" },
  { id: "season_monitoring_check", title: "Season Monitoring Check" },
  { id: "fixture_validation_check", title: "Event / Matchday Validation Check" },
  { id: "stadium_consistency_check", title: "Stadium Consistency Check" },
  { id: "event_quality_check", title: "Event Quality Check" },
  { id: "home_market_check", title: "Home Market Check" },
  { id: "ps_market_channel_check", title: "PS Market & Channel Check" },
  { id: "ps_content_check", title: "PS Content Check" },
  { id: "mm_bsr_consistency_check", title: "MM vs BSR Consistency Check" },
  { id: "audience_spot_range_clean_view", title: "Audience & Spot Price Range Check" },
  { id: "ea_creation_check", title: "EA Creation Check" },
  { id: "previous_delivery_check", title: "Previous Delivery Consistency Check" },
  { id: "live_delayed_check", title: "Live vs Delayed Check" },
];

export default function Page() {
  const [adaptFile, setAdaptFile] = useState<File | null>(null);
  const [roscoFile, setRoscoFile] = useState<File | null>(null);
  const [fixtureFile, setFixtureFile] = useState<File | null>(null);
  const [previousDeliveryFile, setPreviousDeliveryFile] = useState<File | null>(null);
  const [bsrFile, setBsrFile] = useState<File | null>(null);

  const [selectedChecks, setSelectedChecks] = useState<string[]>([]);
  const [btThreshold, setBtThreshold] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);

  const [runMmBsaQc, { isLoading: loading }] = useRunMmBsaQcMutation();
  const [triggerDownloadTemplate] = useLazyDownloadFixtureTemplateQuery();

  const allSelected = selectedChecks.length === QC_CHECKS.length;

  const toggleCheck = (id: string) => {
    setSelectedChecks((prev) =>
      prev.includes(id)
        ? prev.filter((c) => c !== id)
        : [...prev, id]
    );
  };

  const toggleSelectAll = () => {
    setSelectedChecks(allSelected ? [] : QC_CHECKS.map((c) => c.id));
  };

  const handleDownloadTemplate = async () => {
    const blob = await triggerDownloadTemplate().unwrap();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "fixture_template.xlsx";
    a.click();
  };

  const runChecks = async () => {
    if (!adaptFile) return alert("Upload Adapt Export file");
    if (selectedChecks.length === 0) return alert("Select at least one check");

    const formData = new FormData();
    formData.append("adapt_file", adaptFile);
    formData.append("selected_checks", JSON.stringify(selectedChecks));

    if (fixtureFile) formData.append("fixture_file", fixtureFile);
    if (roscoFile) formData.append("rosco_file", roscoFile);
    if (btThreshold) formData.append("bt_threshold", btThreshold);
    if (startDate) formData.append("start_date", startDate);
    if (endDate) formData.append("end_date", endDate);
    if (bsrFile) formData.append("bsr_file", bsrFile);
    if (previousDeliveryFile)
      formData.append("previous_delivery_file", previousDeliveryFile);

    const blob = await runMmBsaQc(formData).unwrap();
    const url = window.URL.createObjectURL(blob);
    setDownloadUrl(url);
  };

  const ready = adaptFile && roscoFile;

  return (
    <div className="flex flex-col gap-6 p-6 w-full">

      {/* HEADER */}
      <div className="flex justify-between items-center">
        <h1 className="text-lg font-semibold text-slate-800 dark:text-slate-200">
          MM BSA Checks
        </h1>

        <button
          onClick={handleDownloadTemplate}
          className="px-3 py-2 text-xs rounded-lg 
          bg-slate-100 dark:bg-slate-800 
          text-slate-700 dark:text-slate-200 
          border border-slate-200 dark:border-slate-700 
          hover:opacity-90"
        >
          Fixture Template
        </button>
      </div>

      <div className="grid grid-cols-3 gap-6">

        {/* LEFT SIDE */}
        <div className="col-span-2 flex flex-col gap-6">

          {/* FILE UPLOAD */}
          <div className="grid grid-cols-5 gap-4">
            {[
              { label: "📂 Adapt File", file: adaptFile, set: setAdaptFile },
              { label: "📑 ROSCO File", file: roscoFile, set: setRoscoFile },
              { label: "📋 Fixture File", file: fixtureFile, set: setFixtureFile },
              { label: "📋 Previous Delivery File", file: previousDeliveryFile, set: setPreviousDeliveryFile },
              { label: "📋 BSR File", file: bsrFile, set: setBsrFile },
            ].map((item, i) => (
              <label
                key={i}
                className={`border border-dashed rounded-xl p-3 text-center cursor-pointer transition
                ${item.file 
                  ? "border-emerald-500 bg-emerald-50 dark:bg-emerald-900/20" 
                  : "border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/40 hover:border-blue-500"
                }`}
              >
                <input
                  type="file"
                  className="hidden"
                  onChange={(e) => item.set(e.target.files?.[0] || null)}
                />

                {/* ICON / TEXT */}
                <div className="flex flex-col items-center justify-center gap-1">
                  <UploadCloud size={18} className="text-slate-400" />

                  <p className="text-xs font-medium text-slate-600 dark:text-slate-300">
                    {item.label}
                  </p>

                  {/* ✅ FILE NAME DISPLAY */}
                  {item.file && (
                    <>
                      <p className="text-[10px] text-emerald-600 dark:text-emerald-400 truncate max-w-full">
                        {item.file.name}
                      </p>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.preventDefault();
                          item.set(null);
                        }}
                        className="text-[10px] text-red-500 hover:underline"
                      >
                        Remove
                      </button>
                    </>
                  )}
                </div>
              </label>
            ))}
          </div>

          {/* CHECKS */}
          <div className="rounded-2xl p-5
            bg-slate-50 dark:bg-slate-900/60
            border border-slate-200 dark:border-slate-700">

            <h3 className="text-sm font-semibold mb-4 text-slate-700 dark:text-slate-200">
              Validation Rules
            </h3>

            <label className="flex items-center gap-2 mb-3 text-sm text-slate-600 dark:text-slate-300">
              <input type="checkbox" checked={allSelected} onChange={toggleSelectAll} />
              Select All
            </label>

            <div className="flex flex-col gap-2 max-h-72 overflow-y-auto">
              {QC_CHECKS.map((c) => (
                <label key={c.id} className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
                  <input
                    type="checkbox"
                    checked={selectedChecks.includes(c.id)}
                    onChange={() => toggleCheck(c.id)}
                  />
                  {c.title}
                </label>
              ))}
            </div>
          </div>

          {/* MONITORING */}
          <div className="rounded-2xl p-5
            bg-slate-50 dark:bg-slate-900/60
            border border-slate-200 dark:border-slate-700">

            <h3 className="text-sm font-semibold mb-4 text-slate-700 dark:text-slate-200">
              Monitoring Setup
            </h3>

            <div className="flex gap-3 mb-4">
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="w-full rounded-lg px-3 py-2 text-sm
                bg-white dark:bg-slate-800
                border border-slate-200 dark:border-slate-700 text-white"
              />

              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="w-full rounded-lg px-3 py-2 text-sm
                bg-white dark:bg-slate-800
                border border-slate-200 dark:border-slate-700 text-white"
              />
            </div>

            <input
              type="number"
              value={btThreshold}
              onChange={(e) => setBtThreshold(e.target.value)}
              placeholder="BT Threshold"
              className="w-full rounded-lg px-3 py-2 text-sm
              bg-white dark:bg-slate-800
              border border-slate-200 dark:border-slate-700"
            />
          </div>
        </div>

        {/* RIGHT PANEL */}
        <div className="rounded-2xl p-6 flex flex-col items-center justify-center gap-4
          bg-slate-50 dark:bg-slate-900/60
          border border-slate-200 dark:border-slate-700">

          <button
            onClick={runChecks}
            disabled={!ready || loading}
            className="w-full py-3 rounded-xl font-semibold text-white
            bg-blue-600 hover:bg-blue-500
            flex items-center justify-center gap-2"
          >
            {loading ? <Loader className="animate-spin" size={16} /> : <UploadCloud size={16} />}
            {loading ? "Running..." : "Run Checks"}
          </button>

          <p className="text-xs text-slate-400">Awaiting inputs</p>

          {downloadUrl && (
            <button
              onClick={() => {
                const a = document.createElement("a");
                a.href = downloadUrl;
                a.download = "MM_BSA_QC_Output.xlsx";
                a.click();
              }}
              className="w-full py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg flex justify-center gap-2"
            >
              <Download size={14} /> Download
            </button>
          )}
        </div>
      </div>
    </div>
  );
}