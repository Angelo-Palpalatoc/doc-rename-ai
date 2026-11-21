"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  AppLogo,
  AttachmentIcon,
  HouseIcon,
} from "@/components/AuthenticIcons";
import { PreviewModal } from "@/components/PreviewModal";
import {
  analyzeDocument,
  exportRenamedZip,
  fetchHealth,
  uploadCompanyList,
} from "@/lib/api";
import type { DocumentItem, HealthResponse } from "@/lib/types";

type AppScreen = "HOME" | "SINGLE" | "BATCH";

interface HistoryEntry {
  id: string;
  target: string;
  source: string;
  timestamp: string;
  sha256: string;
}

function makeId(): string {
  return typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
    ? crypto.randomUUID()
    : `doc-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function sanitizeFilename(stem: string, ext: string): string {
  const cleaned = stem
    .replace(/[<>:"/\\|?*\x00-\x1f]/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/[. ]+$/, "");
  if (!cleaned) return "";
  const safe = /^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?$/i.test(cleaned)
    ? `_${cleaned}`
    : cleaned;
  return `${safe}${ext}`;
}

export default function HomePage() {
  const [screen, setScreen] = useState<AppScreen>("HOME");
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [useLlmFallback, setUseLlmFallback] = useState(true);

  // Optional company registry
  const [companies, setCompanies] = useState<string[]>([]);
  const [companyFilename, setCompanyFilename] = useState<string | null>(null);
  const [manageListOpen, setManageListOpen] = useState(false);

  // Single Document state
  const [singleItem, setSingleItem] = useState<DocumentItem | null>(null);
  const [singleProgress, setSingleProgress] = useState<number | null>(null);
  const [singleStageLabel, setSingleStageLabel] = useState<string>(
    "Working locally…"
  );
  const [singleSavedName, setSingleSavedName] = useState<string | null>(null);
  const [singleConfirmOpen, setSingleConfirmOpen] = useState(false);
  const [singleEvidenceOpen, setSingleEvidenceOpen] = useState(false);
  const [moreMenuOpen, setMoreMenuOpen] = useState(false);

  // Batch Files state
  const [batchItems, setBatchItems] = useState<DocumentItem[]>([]);
  const [batchStarted, setBatchStarted] = useState(false);
  const [batchConfirmId, setBatchConfirmId] = useState<string | null>(null);
  const [batchExporting, setBatchExporting] = useState(false);

  // Shared dialogs, history, snackbar, viewer
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [aboutOpen, setAboutOpen] = useState(false);
  const [viewerItem, setViewerItem] = useState<DocumentItem | null>(null);
  const [snackbarMessage, setSnackbarMessage] = useState<string | null>(null);
  const [inlineError, setInlineError] = useState<string | null>(null);

  const cameraInputRef = useRef<HTMLInputElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const batchInputRef = useRef<HTMLInputElement>(null);
  const companyListInputRef = useRef<HTMLInputElement>(null);
  const singleNameInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    fetchHealth()
      .then(setHealth)
      .catch(() => setHealth(null));
  }, []);

  useEffect(() => {
    if (!snackbarMessage) return;
    const timer = window.setTimeout(() => setSnackbarMessage(null), 3000);
    return () => window.clearTimeout(timer);
  }, [snackbarMessage]);

  const savedHashes = useMemo(
    () => new Set(history.map((h) => h.sha256)),
    [history]
  );

  const handleSelectSingleFile = (file: File) => {
    setInlineError(null);
    setSingleSavedName(null);
    setSingleConfirmOpen(false);
    setMoreMenuOpen(false);
    if (singleItem?.previewUrl) URL.revokeObjectURL(singleItem.previewUrl);

    setSingleItem({
      id: makeId(),
      file,
      previewUrl: URL.createObjectURL(file),
      status: "ready",
      editedName: "",
      approved: false,
      isDuplicate: false,
    });
  };

  const handleAnalyzeSingle = useCallback(async () => {
    if (!singleItem) return;
    setInlineError(null);
    setSingleSavedName(null);
    setSingleProgress(5);
    setSingleStageLabel("Uploading document…");
    setSingleItem((prev) => (prev ? { ...prev, status: "analyzing" } : prev));

    try {
      const analysis = await analyzeDocument(
        singleItem.file,
        companies,
        useLlmFallback,
        (pct, label) => {
          setSingleProgress(pct);
          setSingleStageLabel(label);
        }
      );
      const isDuplicate = savedHashes.has(analysis.sha256);
      setSingleItem((prev) =>
        prev
          ? {
              ...prev,
              status: "ready",
              analysis,
              editedName: analysis.suggested_name ?? "",
              isDuplicate,
            }
          : prev
      );
    } catch (err) {
      const msg =
        err instanceof Error ? err.message : "Failed to read company name.";
      setInlineError(msg);
      setSingleItem((prev) =>
        prev ? { ...prev, status: "error", error: msg } : prev
      );
    }
  }, [companies, savedHashes, singleItem, useLlmFallback]);

  const triggerDownload = (file: File, filename: string) => {
    const url = URL.createObjectURL(file);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleConfirmSingleSave = () => {
    if (!singleItem || !singleItem.analysis) return;
    const target = sanitizeFilename(
      singleItem.editedName,
      singleItem.analysis.extension
    );
    if (!target) return;

    triggerDownload(singleItem.file, target);
    setHistory((prev) => [
      {
        id: makeId(),
        target,
        source: singleItem.file.name,
        timestamp: new Date().toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
        }),
        sha256: singleItem.analysis!.sha256,
      },
      ...prev,
    ]);
    setSingleConfirmOpen(false);
    setSingleSavedName(target);
    setSnackbarMessage("✓ File saved");
  };

  const handleSelectBatchFiles = (fileList: FileList | File[]) => {
    const incoming = Array.from(fileList);
    if (incoming.length === 0) return;
    setInlineError(null);
    setBatchStarted(false);

    for (const old of batchItems) {
      if (old.previewUrl) URL.revokeObjectURL(old.previewUrl);
    }

    setBatchItems(
      incoming.map((file) => ({
        id: makeId(),
        file,
        previewUrl: URL.createObjectURL(file),
        status: "ready",
        editedName: "",
        approved: false,
        isDuplicate: false,
      }))
    );
  };

  const handleStartBatch = async () => {
    if (batchItems.length === 0) return;
    setInlineError(null);
    setBatchStarted(true);

    setBatchItems((prev) =>
      prev.map((item) => ({ ...item, status: "analyzing", error: undefined }))
    );

    const seenInBatch = new Set<string>(savedHashes);

    await Promise.all(
      batchItems.map(async (entry) => {
        try {
          const analysis = await analyzeDocument(
            entry.file,
            companies,
            useLlmFallback
          );
          const isDuplicate = seenInBatch.has(analysis.sha256);
          seenInBatch.add(analysis.sha256);

          setBatchItems((prev) =>
            prev.map((item) =>
              item.id === entry.id
                ? {
                    ...item,
                    status: "ready",
                    analysis,
                    editedName: analysis.suggested_name ?? "",
                    isDuplicate,
                  }
                : item
            )
          );
        } catch (err) {
          setBatchItems((prev) =>
            prev.map((item) =>
              item.id === entry.id
                ? {
                    ...item,
                    status: "error",
                    error:
                      err instanceof Error ? err.message : "Analysis failed.",
                  }
                : item
            )
          );
        }
      })
    );
  };

  const handleConfirmBatchSave = () => {
    if (!batchConfirmId) return;
    const item = batchItems.find((i) => i.id === batchConfirmId);
    if (!item || !item.analysis) return;

    const target = sanitizeFilename(item.editedName, item.analysis.extension);
    if (!target) return;

    triggerDownload(item.file, target);
    setHistory((prev) => [
      {
        id: makeId(),
        target,
        source: item.file.name,
        timestamp: new Date().toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
        }),
        sha256: item.analysis!.sha256,
      },
      ...prev,
    ]);
    setBatchItems((prev) =>
      prev.map((doc) =>
        doc.id === item.id ? { ...doc, approved: true } : doc
      )
    );
    setBatchConfirmId(null);
    setSnackbarMessage("✓ File saved");
  };

  const handleBatchExportZip = async () => {
    const ready = batchItems.filter(
      (i) => i.status === "ready" && i.analysis && i.editedName.trim()
    );
    if (ready.length === 0) return;

    setBatchExporting(true);
    setInlineError(null);
    try {
      const blob = await exportRenamedZip(
        ready.map((i) => ({ file: i.file, targetName: i.editedName.trim() }))
      );
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "renamed-documents.zip";
      a.click();
      URL.revokeObjectURL(url);
      setSnackbarMessage(`✓ Exported ${ready.length} files as ZIP`);
    } catch (err) {
      setInlineError(
        err instanceof Error ? err.message : "Failed to export ZIP."
      );
    } finally {
      setBatchExporting(false);
    }
  };

  const handleImportCompanyList = async (file: File) => {
    setInlineError(null);
    try {
      const res = await uploadCompanyList(file);
      setCompanies(res.companies);
      setCompanyFilename(res.source_filename);
    } catch (err) {
      setInlineError(
        err instanceof Error ? err.message : "Failed to import company list."
      );
    }
  };

  const singleExt = singleItem?.analysis?.extension || "";
  const singleProposal = singleItem?.analysis
    ? sanitizeFilename(singleItem.editedName, singleExt)
    : "";
  const singleBusy = singleItem?.status === "analyzing";
  const batchCompletedCount = batchItems.filter((i) => i.approved).length;
  const batchConfirmItem = batchItems.find((i) => i.id === batchConfirmId);

  const companyListRow = (
    <div className="flex items-center justify-between gap-3 py-1">
      <div className="min-w-0 flex-1">
        <p className="text-xs font-medium text-[#162B43]">Company list</p>
        <p className="truncate text-xs text-[#536477]">
          {companies.length === 0
            ? "Optional"
            : `${companyFilename} · ${companies.length} companies`}
        </p>
      </div>
      <button
        type="button"
        onClick={() =>
          companies.length === 0
            ? companyListInputRef.current?.click()
            : setManageListOpen(true)
        }
        className="shrink-0 rounded-lg px-3 py-1.5 text-sm font-medium text-[#0054A4] hover:bg-[#0054A4]/10"
      >
        {companies.length === 0 ? "Import Excel" : "Change"}
      </button>
    </div>
  );

  return (
    <div className="flex min-h-[100dvh] flex-col overflow-x-hidden bg-[#F3F6FA] text-[#162B43]">
      {/* Hidden file inputs */}
      <input
        ref={cameraInputRef}
        type="file"
        accept="image/*"
        capture="environment"
        className="hidden"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) handleSelectSingleFile(f);
          e.target.value = "";
        }}
      />
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.png,.jpg,.jpeg"
        className="hidden"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) handleSelectSingleFile(f);
          e.target.value = "";
        }}
      />
      <input
        ref={batchInputRef}
        type="file"
        multiple
        accept=".pdf,.png,.jpg,.jpeg"
        className="hidden"
        onChange={(e) => {
          if (e.target.files) handleSelectBatchFiles(e.target.files);
          e.target.value = "";
        }}
      />
      <input
        ref={companyListInputRef}
        type="file"
        accept=".xlsx,.csv"
        className="hidden"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) handleImportCompanyList(f);
          e.target.value = "";
        }}
      />

      {/* Top App Bar (mirrors DemoScreen.kt lines 153-173) */}
      <header className="sticky top-0 z-20 bg-white shadow-xs">
        <div className="mx-auto flex max-w-4xl items-center gap-2 px-3 py-2.5">
          {screen !== "HOME" && (
            <button
              type="button"
              onClick={() => {
                setScreen("HOME");
                setInlineError(null);
              }}
              aria-label="Home"
              className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-[#0054A4] hover:bg-[#0054A4]/10"
            >
              <HouseIcon className="h-6 w-6" />
            </button>
          )}

          <div className="flex min-w-0 flex-1 items-center justify-between gap-2 pl-1">
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <AppLogo className="h-6 w-6" />
                <h1 className="truncate text-lg font-bold tracking-tight text-[#162B43]">
                  DocRename AI
                </h1>
              </div>
              <p className="text-[11px] text-[#536477]">
                Scan · Review · Save a copy
              </p>
            </div>

            <div className="flex items-center gap-2.5">
              <button
                type="button"
                onClick={() => setUseLlmFallback((v) => !v)}
                title={
                  health
                    ? `OCR: ${health.ocr_engine} · LLM: ${health.llm_provider}`
                    : "Toggle AI fallback"
                }
                className={`rounded-full border px-2.5 py-1 text-[11px] font-medium transition-colors ${
                  useLlmFallback
                    ? "border-[#0054A4]/30 bg-[#0054A4]/10 text-[#0054A4]"
                    : "border-slate-300 bg-slate-100 text-[#536477]"
                }`}
              >
                AI: {useLlmFallback ? "On" : "Off"}
              </button>
              <span className="text-[11px] font-semibold tracking-wider text-[#B51F32]">
                DEMO
              </span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content Body */}
      <main className="mx-auto flex w-full max-w-4xl flex-1 flex-col gap-3 px-4 py-4">
        {/* Busy progress bar */}
        {singleBusy && (
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-xs font-semibold text-[#0054A4]">
              <span>{singleStageLabel}</span>
              {singleProgress !== null && <span>{singleProgress}%</span>}
            </div>
            <div className="h-1 w-full overflow-hidden rounded-full bg-[#0054A4]/20">
              {singleProgress !== null ? (
                <div
                  className="h-full rounded-full bg-[#0054A4] transition-all duration-200 ease-out"
                  style={{ width: `${Math.max(5, singleProgress)}%` }}
                />
              ) : (
                <div className="progress-indeterminate h-full rounded-full bg-[#0054A4]" />
              )}
            </div>
          </div>
        )}

        {/* Inline Error Notice */}
        {inlineError && (
          <div className="flex items-center justify-between gap-2 rounded-[10px] bg-[#B51F32]/[0.08] px-3 py-2.5">
            <p className="text-sm font-medium text-[#B51F32]">{inlineError}</p>
            <button
              type="button"
              onClick={() => setInlineError(null)}
              aria-label="Dismiss message"
              className="px-2 text-lg leading-none text-[#B51F32]"
            >
              ×
            </button>
          </div>
        )}

        {/* HOME SCREEN (mirrors DemoScreen.kt lines 220-228) */}
        {screen === "HOME" && (
          <div className="mx-auto flex w-full max-w-lg flex-col gap-3 pt-2">
            <h2 className="text-xl font-bold text-[#162B43]">
              How would you like to start?
            </h2>

            <section className="rounded-2xl bg-white p-4 shadow-xs space-y-2.5">
              <button
                type="button"
                onClick={() => setScreen("SINGLE")}
                className="w-full rounded-full bg-[#0054A4] px-5 py-3 text-sm font-semibold text-white shadow-xs hover:bg-[#00468a]"
              >
                {singleItem ? "Continue Single Document" : "Single Document"}
              </button>
              <p className="text-xs text-[#536477]">Camera, photo or file</p>
            </section>

            <section className="rounded-2xl bg-white p-4 shadow-xs">
              <button
                type="button"
                onClick={() => setScreen("BATCH")}
                className="w-full rounded-full border border-[#0054A4] bg-white px-5 py-3 text-sm font-semibold text-[#0054A4] hover:bg-[#0054A4]/5"
              >
                Batch files
              </button>
            </section>
          </div>
        )}

        {/* SINGLE DOCUMENT SCREEN (mirrors DemoScreen.kt lines 236-278) */}
        {screen === "SINGLE" && (
          <div className="grid flex-1 gap-4 md:grid-cols-2 md:items-start">
            {/* Left / Top Source Column */}
            <div className="flex flex-col gap-3">
              <div className="rounded-2xl bg-white px-4 py-3 shadow-xs space-y-2">
                {companyListRow}

                {/* FileAttachment Card (mirrors lines 359-387) */}
                {singleItem && (
                  <button
                    type="button"
                    disabled={singleBusy}
                    onClick={() => setViewerItem(singleItem)}
                    className="flex w-full items-center gap-3 rounded-xl border border-slate-200 bg-[#F3F6FA] p-3 text-left transition-colors hover:border-[#0054A4]/40 disabled:opacity-40"
                  >
                    <div
                      className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-[9px] ${
                        singleItem.file.type.startsWith("image/")
                          ? "bg-[#0054A4]/10"
                          : "bg-[#B51F32]/10"
                      }`}
                    >
                      <AttachmentIcon
                        isImage={singleItem.file.type.startsWith("image/")}
                      />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-semibold text-[#162B43]">
                        {singleItem.file.name}
                      </p>
                      <p className="text-[11px] font-medium uppercase text-[#536477]">
                        {singleItem.file.name.split(".").pop() || "FILE"} · Tap
                        to preview
                      </p>
                    </div>
                    <svg
                      viewBox="0 0 16 16"
                      className="h-4 w-4 shrink-0 text-[#536477]"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth={1.8}
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <path d="M5.5 3.2 L11.2 8 L5.5 12.8" />
                    </svg>
                  </button>
                )}

                {singleItem?.analysis?.ambiguous && !singleItem.isDuplicate && (
                  <p className="text-xs font-medium text-[#805300]">
                    Multiple company names detected. Review the document and
                    confirm the exact name.
                  </p>
                )}
              </div>

              {/* Desktop Input Actions */}
              <div className="hidden gap-2 md:flex">
                <button
                  type="button"
                  disabled={singleBusy}
                  onClick={() => cameraInputRef.current?.click()}
                  className="flex-1 rounded-full bg-[#0054A4] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#00468a] disabled:opacity-40"
                >
                  Scan with camera
                </button>
                <button
                  type="button"
                  disabled={singleBusy}
                  onClick={() => fileInputRef.current?.click()}
                  className="flex-1 rounded-full border border-[#0054A4] bg-white px-4 py-2.5 text-sm font-semibold text-[#0054A4] hover:bg-[#0054A4]/5 disabled:opacity-40"
                >
                  Open file
                </button>
              </div>
            </div>

            {/* Right / Bottom Review Column */}
            <div className="flex flex-col gap-3">
              {singleSavedName && (
                <div className="rounded-[10px] bg-[#14643C]/[0.08] px-3.5 py-3 space-y-1">
                  <p className="text-sm font-semibold text-[#14643C]">
                    File saved
                  </p>
                  <p className="text-xs text-[#162B43] break-all">
                    {singleSavedName}
                  </p>
                </div>
              )}

              {singleItem?.isDuplicate && !singleSavedName && (
                <div className="rounded-[10px] bg-[#805300]/[0.08] px-3.5 py-3 space-y-1">
                  <p className="text-sm font-semibold text-[#805300]">
                    Document already renamed
                  </p>
                  <p className="text-xs text-[#536477]">
                    Matching SHA-256 file content was already exported in this
                    session.
                  </p>
                </div>
              )}

              {singleItem &&
                !singleItem.analysis &&
                !singleBusy &&
                !singleSavedName && (
                  <button
                    type="button"
                    onClick={handleAnalyzeSingle}
                    className="w-full rounded-full bg-[#0054A4] px-5 py-3 text-sm font-semibold text-white shadow-xs hover:bg-[#00468a]"
                  >
                    Read company name
                  </button>
                )}

              {singleItem?.analysis &&
                !singleItem.isDuplicate &&
                !singleSavedName && (
                  <div className="rounded-2xl bg-white p-4 shadow-xs space-y-4">
                    <div>
                      <label
                        htmlFor="company-name-input"
                        className="mb-1 block text-xs font-medium text-[#536477]"
                      >
                        Company name
                      </label>
                      <input
                        ref={singleNameInputRef}
                        id="company-name-input"
                        type="text"
                        value={singleItem.editedName}
                        onChange={(e) =>
                          setSingleItem((prev) =>
                            prev
                              ? { ...prev, editedName: e.target.value }
                              : prev
                          )
                        }
                        placeholder="Enter verified company name"
                        className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm text-[#162B43] focus:border-[#0054A4] focus:outline-none focus:ring-2 focus:ring-[#0054A4]/20"
                      />
                    </div>

                    <div className="flex items-center justify-between gap-2">
                      <div className="min-w-0 flex-1">
                        <p className="text-[11px] text-[#536477]">File name</p>
                        <p className="truncate text-sm font-medium text-[#162B43]">
                          {singleProposal || "Enter a company name"}
                        </p>
                      </div>

                      <div className="relative">
                        <button
                          type="button"
                          onClick={() => setMoreMenuOpen((v) => !v)}
                          className="rounded-lg px-3 py-1.5 text-sm font-medium text-[#0054A4] hover:bg-[#0054A4]/10"
                        >
                          More
                        </button>
                        {moreMenuOpen && (
                          <>
                            <div
                              className="fixed inset-0 z-10"
                              onClick={() => setMoreMenuOpen(false)}
                            />
                            <div className="absolute right-0 z-20 mt-1 w-44 rounded-xl border border-slate-200 bg-white py-1 shadow-lg">
                              <button
                                type="button"
                                onClick={() => {
                                  setMoreMenuOpen(false);
                                  setSingleEvidenceOpen(true);
                                }}
                                className="block min-h-[40px] w-full px-3.5 py-2 text-left text-sm text-[#162B43] hover:bg-[#F3F6FA]"
                              >
                                OCR evidence
                              </button>
                              <button
                                type="button"
                                onClick={() => {
                                  setMoreMenuOpen(false);
                                  handleAnalyzeSingle();
                                }}
                                className="block min-h-[40px] w-full px-3.5 py-2 text-left text-sm text-[#162B43] hover:bg-[#F3F6FA]"
                              >
                                Read again
                              </button>
                            </div>
                          </>
                        )}
                      </div>
                    </div>

                    <button
                      type="button"
                      disabled={!singleProposal}
                      onClick={() => setSingleConfirmOpen(true)}
                      className="w-full rounded-full bg-[#0054A4] px-5 py-3 text-sm font-semibold text-white shadow-xs hover:bg-[#00468a] disabled:opacity-40"
                    >
                      Save renamed copy
                    </button>
                  </div>
                )}

              {/* Mobile Input Actions (bottom of Single flow, mirrors line 276) */}
              <div className="flex gap-2 pt-1 md:hidden">
                <button
                  type="button"
                  disabled={singleBusy}
                  onClick={() => cameraInputRef.current?.click()}
                  className="min-h-[44px] flex-1 whitespace-nowrap rounded-full bg-[#0054A4] px-3 py-2.5 text-[13px] font-semibold text-white hover:bg-[#00468a] disabled:opacity-40 sm:text-sm"
                >
                  Scan with camera
                </button>
                <button
                  type="button"
                  disabled={singleBusy}
                  onClick={() => fileInputRef.current?.click()}
                  className="min-h-[44px] flex-1 whitespace-nowrap rounded-full border border-[#0054A4] bg-white px-3 py-2.5 text-[13px] font-semibold text-[#0054A4] hover:bg-[#0054A4]/5 disabled:opacity-40 sm:text-sm"
                >
                  Open file
                </button>
              </div>
            </div>
          </div>
        )}

        {/* BATCH FILES SCREEN (mirrors BatchScreen.kt) */}
        {screen === "BATCH" && (
          <div className="mx-auto flex w-full max-w-2xl flex-col gap-3">
            <div className="rounded-2xl bg-white px-4 py-3 shadow-xs space-y-2">
              <div className="flex items-center justify-between gap-3 py-1">
                <p className="min-w-0 flex-1 truncate text-sm text-[#162B43]">
                  {batchItems.length === 0
                    ? "No source files selected"
                    : `${batchItems.length} files selected`}
                </p>
                <button
                  type="button"
                  onClick={() => batchInputRef.current?.click()}
                  className="shrink-0 rounded-lg px-3 py-1.5 text-sm font-medium text-[#0054A4] hover:bg-[#0054A4]/10"
                >
                  Choose source files
                </button>
              </div>

              {companyListRow}

              <div className="flex flex-col gap-2 pt-1 sm:flex-row">
                <button
                  type="button"
                  disabled={batchItems.length === 0}
                  onClick={handleStartBatch}
                  className="flex-1 rounded-full bg-[#0054A4] px-5 py-2.5 text-sm font-semibold text-white hover:bg-[#00468a] disabled:opacity-40"
                >
                  Start batch rename
                </button>
                {batchStarted && (
                  <button
                    type="button"
                    disabled={batchExporting}
                    onClick={handleBatchExportZip}
                    className="rounded-full border border-[#0054A4] bg-white px-4 py-2.5 text-sm font-semibold text-[#0054A4] hover:bg-[#0054A4]/5 disabled:opacity-40"
                  >
                    {batchExporting ? "Exporting…" : "Export all ZIP"}
                  </button>
                )}
              </div>
            </div>

            {batchStarted && (
              <>
                {(() => {
                  const analyzedCount = batchItems.filter(
                    (i) => i.status !== "analyzing"
                  ).length;
                  const batchBusy = analyzedCount < batchItems.length;
                  const pct =
                    batchItems.length > 0
                      ? Math.round((analyzedCount / batchItems.length) * 100)
                      : 0;
                  return (
                    <div className="space-y-1.5">
                      <div className="flex items-center justify-between text-xs text-[#536477]">
                        <span>
                          {batchBusy
                            ? `Reading ${analyzedCount} of ${batchItems.length} files…`
                            : `${batchCompletedCount} of ${batchItems.length} saved`}
                        </span>
                        {batchBusy && (
                          <span className="font-semibold text-[#0054A4]">
                            {pct}%
                          </span>
                        )}
                      </div>
                      {batchBusy && (
                        <div className="h-1 w-full overflow-hidden rounded-full bg-[#0054A4]/20">
                          <div
                            className="h-full rounded-full bg-[#0054A4] transition-all duration-300 ease-out"
                            style={{ width: `${Math.max(6, pct)}%` }}
                          />
                        </div>
                      )}
                    </div>
                  );
                })()}

                <div className="space-y-2.5">
                  {batchItems.map((item) => (
                    <div
                      key={item.id}
                      className="flex flex-col gap-2.5 rounded-[10px] bg-white p-3 shadow-xs sm:flex-row sm:items-center sm:gap-3"
                    >
                      <div className="min-w-0 flex-1 space-y-1.5">
                        <button
                          type="button"
                          disabled={item.status === "analyzing"}
                          onClick={() => setViewerItem(item)}
                          className="block max-w-full truncate text-left text-sm font-medium text-[#0054A4] hover:underline disabled:opacity-50"
                        >
                          {item.file.name}
                        </button>

                        {item.status === "analyzing" ? (
                          <div className="h-1 w-full overflow-hidden rounded-full bg-[#0054A4]/20">
                            <div className="progress-indeterminate h-full rounded-full bg-[#0054A4]" />
                          </div>
                        ) : (
                          <input
                            type="text"
                            value={item.editedName}
                            onChange={(e) =>
                              setBatchItems((prev) =>
                                prev.map((doc) =>
                                  doc.id === item.id
                                    ? { ...doc, editedName: e.target.value }
                                    : doc
                                )
                              )
                            }
                            placeholder="Company name"
                            className="min-h-[42px] w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-[#162B43] focus:border-[#0054A4] focus:outline-none"
                          />
                        )}

                        {item.isDuplicate && (
                          <p className="text-xs text-[#805300]">
                            Duplicate content (SHA-256 match)
                          </p>
                        )}
                        {item.error && (
                          <p className="text-xs text-[#B51F32]">{item.error}</p>
                        )}
                      </div>

                      <button
                        type="button"
                        disabled={
                          item.status === "analyzing" || !item.editedName.trim()
                        }
                        onClick={() => setBatchConfirmId(item.id)}
                        className={`min-h-[42px] shrink-0 rounded-full px-4 py-2 text-sm font-semibold text-white disabled:opacity-40 ${
                          item.approved
                            ? "bg-[#14643C]"
                            : "bg-[#0054A4] hover:bg-[#00468a]"
                        }`}
                      >
                        {item.approved ? "Saved" : "Save"}
                      </button>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        )}
      </main>

      {/* Bottom Bar + Snackbar (mirrors DemoScreen.kt lines 174-198) */}
      <footer className="sticky bottom-0 z-20 border-t border-slate-200/70 bg-[#F3F6FA]/95 pb-[env(safe-area-inset-bottom)] backdrop-blur-xs">
        <div className="mx-auto max-w-4xl px-4 pb-2 pt-1.5">
          {snackbarMessage && (
            <div className="mb-2 flex justify-center">
              <div className="inline-flex items-center gap-3 rounded-[10px] bg-[#162B43] px-4 py-2.5 text-sm text-white shadow-md">
                <span>{snackbarMessage}</span>
              </div>
            </div>
          )}

          <div className="flex items-center justify-between">
            <button
              type="button"
              onClick={() => setHistoryOpen(true)}
              className="rounded-lg px-2 py-2 text-sm font-medium text-[#0054A4] hover:bg-[#0054A4]/10"
            >
              Export history
            </button>
            <button
              type="button"
              onClick={() => setAboutOpen(true)}
              className="rounded-lg px-2 py-2 text-sm font-medium text-[#0054A4] hover:bg-[#0054A4]/10"
            >
              About
            </button>
          </div>
        </div>
      </footer>

      {/* Single Save Confirmation Dialog (mirrors lines 461-474) */}
      {singleConfirmOpen && singleItem && singleItem.analysis && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/45 p-4">
          <div className="w-full max-w-sm rounded-3xl bg-white p-6 shadow-xl space-y-4">
            <h3 className="text-lg font-semibold text-[#162B43]">
              Is the company name correct?
            </h3>
            <div className="space-y-2.5 text-sm">
              <p className="font-bold text-[#162B43]">
                {singleItem.editedName}
              </p>
              <div>
                <p className="text-[11px] text-[#536477]">File name</p>
                <p className="break-all text-[#162B43]">{singleProposal}</p>
              </div>
              <div>
                <p className="text-[11px] text-[#536477]">Source method</p>
                <p className="text-xs text-[#536477]">
                  {singleItem.analysis.method} (
                  {Math.round(singleItem.analysis.confidence * 100)}%)
                </p>
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => {
                  setSingleConfirmOpen(false);
                  window.setTimeout(() => singleNameInputRef.current?.focus(), 80);
                }}
                className="rounded-full px-4 py-2 text-sm font-medium text-[#0054A4] hover:bg-[#0054A4]/10"
              >
                Edit name
              </button>
              <button
                type="button"
                onClick={handleConfirmSingleSave}
                className="rounded-full px-4 py-2 text-sm font-semibold text-[#0054A4] hover:bg-[#0054A4]/10"
              >
                Yes, save
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Batch Save Confirmation Dialog (mirrors lines 115-121) */}
      {batchConfirmItem && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/45 p-4">
          <div className="w-full max-w-sm rounded-3xl bg-white p-6 shadow-xl space-y-4">
            <h3 className="text-lg font-semibold text-[#162B43]">
              Is the company name correct?
            </h3>
            <p className="text-sm font-medium text-[#162B43]">
              {batchConfirmItem.editedName}
            </p>
            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setBatchConfirmId(null)}
                className="rounded-full px-4 py-2 text-sm font-medium text-[#0054A4] hover:bg-[#0054A4]/10"
              >
                Edit name
              </button>
              <button
                type="button"
                onClick={handleConfirmBatchSave}
                className="rounded-full px-4 py-2 text-sm font-semibold text-[#0054A4] hover:bg-[#0054A4]/10"
              >
                Yes, save
              </button>
            </div>
          </div>
        </div>
      )}

      {/* OCR Evidence Dialog (mirrors lines 475-479) */}
      {singleEvidenceOpen && singleItem?.analysis && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/45 p-4">
          <div className="w-full max-w-md rounded-3xl bg-white p-6 shadow-xl space-y-4">
            <h3 className="text-lg font-semibold text-[#162B43]">
              OCR evidence
            </h3>
            <div className="max-h-72 overflow-auto space-y-2 text-xs text-[#162B43]">
              {singleItem.analysis.evidence && (
                <p className="rounded-lg bg-[#14643C]/10 px-3 py-2 font-medium text-[#14643C]">
                  Matched: {singleItem.analysis.evidence}
                </p>
              )}
              {singleItem.analysis.llm_reasoning && (
                <p className="rounded-lg bg-[#0054A4]/10 px-3 py-2 text-[#0054A4]">
                  AI note: {singleItem.analysis.llm_reasoning}
                </p>
              )}
              <p className="whitespace-pre-wrap font-mono text-[11px] text-[#536477]">
                {singleItem.analysis.ocr_excerpt ||
                  "No readable text. Check the document and enter the company name manually."}
              </p>
            </div>
            <div className="flex justify-end">
              <button
                type="button"
                onClick={() => setSingleEvidenceOpen(false)}
                className="rounded-full px-4 py-2 text-sm font-semibold text-[#0054A4] hover:bg-[#0054A4]/10"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Manage Company List Dialog (mirrors CompanyListControls.kt lines 30-40) */}
      {manageListOpen && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/45 p-4">
          <div className="w-full max-w-sm rounded-3xl bg-white p-6 shadow-xl space-y-4">
            <h3 className="text-lg font-semibold text-[#162B43]">
              Company list
            </h3>
            <p className="text-sm text-[#536477]">
              {companyFilename}
              <br />
              {companies.length} companies loaded in this session.
            </p>
            <div className="flex flex-wrap justify-end gap-1 pt-2">
              <button
                type="button"
                onClick={() => {
                  setManageListOpen(false);
                  setCompanies([]);
                  setCompanyFilename(null);
                }}
                className="rounded-full px-3 py-2 text-sm font-medium text-[#B51F32] hover:bg-[#B51F32]/10"
              >
                Remove list
              </button>
              <button
                type="button"
                onClick={() => setManageListOpen(false)}
                className="rounded-full px-3 py-2 text-sm font-medium text-[#536477] hover:bg-slate-100"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => {
                  setManageListOpen(false);
                  companyListInputRef.current?.click();
                }}
                className="rounded-full px-3 py-2 text-sm font-semibold text-[#0054A4] hover:bg-[#0054A4]/10"
              >
                Replace list
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Export History Dialog (mirrors lines 122-150) */}
      {historyOpen && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/45 p-4">
          <div className="w-full max-w-md rounded-3xl bg-white p-6 shadow-xl space-y-4">
            <h3 className="text-lg font-semibold text-[#162B43]">
              Export history
            </h3>
            <div className="max-h-80 overflow-auto space-y-3">
              {history.length === 0 ? (
                <p className="text-sm text-[#536477]">No exports yet.</p>
              ) : (
                history.map((entry) => (
                  <div
                    key={entry.id}
                    className="border-b border-slate-100 pb-2.5 last:border-0"
                  >
                    <p className="text-sm font-medium text-[#162B43] break-all">
                      {entry.target}
                    </p>
                    <p className="text-xs text-[#536477]">
                      {entry.timestamp} · {entry.source}
                    </p>
                  </div>
                ))
              )}
            </div>
            <div className="flex justify-end">
              <button
                type="button"
                onClick={() => setHistoryOpen(false)}
                className="rounded-full px-4 py-2 text-sm font-semibold text-[#0054A4] hover:bg-[#0054A4]/10"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* About Dialog (mirrors lines 110-114) */}
      {aboutOpen && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/45 p-4">
          <div className="w-full max-w-sm rounded-3xl bg-white p-6 shadow-xl space-y-4">
            <h3 className="text-lg font-semibold text-[#162B43]">
              About this demo
            </h3>
            <p className="text-sm leading-relaxed text-[#536477]">
              Documents are processed through local PyMuPDF + RapidOCR (ONNX)
              with deterministic corporate naming rules and an optional
              structured-output LLM fallback. Original files stay unchanged.
            </p>
            <div className="flex justify-end">
              <button
                type="button"
                onClick={() => setAboutOpen(false)}
                className="rounded-full px-4 py-2 text-sm font-semibold text-[#0054A4] hover:bg-[#0054A4]/10"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Fullscreen Viewer (mirrors FullscreenViewer lines 514-548) */}
      {viewerItem && viewerItem.previewUrl && (
        <PreviewModal
          file={viewerItem.file}
          previewUrl={viewerItem.previewUrl}
          onClose={() => setViewerItem(null)}
        />
      )}
    </div>
  );
}
