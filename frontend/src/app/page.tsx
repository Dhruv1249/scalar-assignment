"use client";

import React, { useState, useRef } from "react";

export default function Home() {
  const [file, setFile] = useState<File | null>(null);

  const [locale, setLocale] = useState<string>("en_US");
  const [scoreThreshold, setScoreThreshold] = useState<string>("0.7");
  const [indiaPack, setIndiaPack] = useState<boolean>(true);
  const [allowlistText, setAllowlistText] = useState<string>("");
  const [isDragOver, setIsDragOver] = useState<boolean>(false);

  const [loading, setLoading] = useState<boolean>(false);
  const [progressPercent, setProgressPercent] = useState<number>(0);
  const [progressStatus, setProgressStatus] = useState<string>("");

  const [redactedResult, setRedactedResult] = useState<{
    downloadUrl: string;
    filename: string;
    subjectEntity: string;
    piiCount: string;
  } | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile.name.endsWith(".docx")) {
        setFile(droppedFile);
      } else {
        alert("Only .docx files are supported.");
      }
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      alert("Please select a .docx document to redact.");
      return;
    }

    setLoading(true);
    setRedactedResult(null);
    setProgressPercent(20);
    setProgressStatus("Uploading document and initializing spaCy NER engine...");

    const progressInterval = setInterval(() => {
      setProgressPercent((prev) => {
        if (prev < 85) {
          const next = prev + 15;
          if (next === 50) setProgressStatus("Scanning PII spans across paragraphs and tables...");
          if (next === 80) setProgressStatus("Generating consistent fake replacements...");
          return next;
        }
        return prev;
      });
    }, 800);

    const formData = new FormData();
    formData.append("file", file);
    formData.append("locale", locale);
    formData.append("score_threshold", scoreThreshold);

    if (indiaPack) {
      formData.append("recognizer_pack", "in");
    }

    if (allowlistText.trim()) {
      const formattedAllowlist = allowlistText
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean)
        .join("\n");
      formData.append("org_allowlist_text", formattedAllowlist);
    }

    try {
      const apiBase = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");
      const res = await fetch(`${apiBase}/api/redact`, {
        method: "POST",
        body: formData,
      });

      clearInterval(progressInterval);

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({ detail: "Redaction request failed." }));
        throw new Error(errorData.detail || "Server error during redaction processing.");
      }

      setProgressPercent(100);
      setProgressStatus("Done!");

      const blob = await res.blob();
      const downloadUrl = URL.createObjectURL(blob);
      const subjectEntity = res.headers.get("X-Subject-Entity") || "Auto-Detected";
      const piiCount = res.headers.get("X-Total-PII-Count") || "0";
      const outFilename = `${file.name.replace(".docx", "")}_redacted.docx`;

      setTimeout(() => {
        setLoading(false);
        setRedactedResult({
          downloadUrl,
          filename: outFilename,
          subjectEntity,
          piiCount,
        });
      }, 500);
    } catch (err: unknown) {
      clearInterval(progressInterval);
      setLoading(false);
      const errorMessage = err instanceof Error ? err.message : "Network error or API server unreachable.";
      alert(`Error: ${errorMessage}`);
    }
  };

  return (
    <div className="w-full max-w-[640px] my-8">
      {/* Header */}
      <header className="text-center mb-8">
        <h1 className="text-3xl sm:text-4xl font-extrabold text-[var(--text-primary)] tracking-tight mb-2 font-[family-name:var(--font-nunito)]">
          PII Redaction Studio
        </h1>
        <p className="text-sm sm:text-base text-[var(--text-secondary)]">
          Tactile, privacy-first document sanitizer powered by Presidio & spaCy
        </p>
      </header>

      {/* Main Soft UI Card */}
      <div className="neu-card p-6 sm:p-9">
        <form onSubmit={handleSubmit}>
          {/* File Dropzone */}
          <div
            className={`neu-dropzone p-8 text-center cursor-pointer relative ${
              isDragOver ? "dragover" : ""
            }`}
            onDragOver={(e) => {
              e.preventDefault();
              setIsDragOver(true);
            }}
            onDragLeave={(e) => {
              e.preventDefault();
              setIsDragOver(false);
            }}
            onDrop={handleFileDrop}
            onClick={() => fileInputRef.current?.click()}
          >
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileChange}
              accept=".docx"
              className="hidden"
            />
            <div className="flex justify-center text-[var(--accent)] mb-4">
              <svg
                width="40"
                height="40"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
                <path d="M12 18v-6" />
                <path d="m9 15 3-3 3 3" />
              </svg>
            </div>
            <div className="text-base font-semibold text-[var(--text-primary)] mb-1">
              {file ? file.name : "Drag & drop your .docx file here"}
            </div>
            <div className="text-xs text-[var(--text-muted)]">
              {file ? `${(file.size / 1024).toFixed(1)} KB selected` : "or click to browse your computer"}
            </div>
          </div>

          {/* Options Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-5 mt-7">

            <div className="flex flex-col gap-2">
              <label className="text-xs font-semibold text-[var(--text-muted)] tracking-wider uppercase">
                Fake Locale
              </label>
              <select
                value={locale}
                onChange={(e) => setLocale(e.target.value)}
                className="neu-select px-4 py-3 text-sm"
              >
                <option value="en_US">English (US) - en_US</option>
                <option value="en_IN">English (India) - en_IN</option>
                <option value="en_GB">English (UK) - en_GB</option>
              </select>
            </div>

            <div className="flex flex-col gap-2">
              <label className="text-xs font-semibold text-[var(--text-muted)] tracking-wider uppercase">
                India Identifiers Pack
              </label>
              <div className="neu-toggle-wrapper flex items-center justify-between px-4 py-3">
                <span className="text-xs sm:text-sm font-medium text-[var(--text-secondary)]">
                  PAN / CIN / DIN
                </span>
                <div
                  className={`neu-toggle ${indiaPack ? "is-on" : ""}`}
                  onClick={() => setIndiaPack(!indiaPack)}
                />
              </div>
            </div>

            <div className="flex flex-col gap-2">
              <label className="text-xs font-semibold text-[var(--text-muted)] tracking-wider uppercase">
                Confidence Threshold
              </label>
              <select
                value={scoreThreshold}
                onChange={(e) => setScoreThreshold(e.target.value)}
                className="neu-select px-4 py-3 text-sm"
              >
                <option value="0.7">0.7 (Corpus Optimal)</option>
                <option value="0.6">0.6 (Balanced)</option>
                <option value="0.5">0.5 (Higher Recall)</option>
                <option value="0.4">0.4 (Maximum Recall)</option>
              </select>
            </div>
          </div>

          <div className="flex flex-col gap-2 mt-5">
            <label className="text-xs font-semibold text-[var(--text-muted)] tracking-wider uppercase">
              Custom Org Allowlist (Optional)
            </label>
            <input
              type="text"
              value={allowlistText}
              onChange={(e) => setAllowlistText(e.target.value)}
              className="neu-input px-4 py-3 text-sm"
              placeholder="e.g. SEBI, RBI, BSE, NSE (comma separated)"
            />
          </div>

          {/* Action Button */}
          <div className="mt-8">
            <button
              type="submit"
              disabled={loading}
              className="neu-btn-primary w-full py-4 text-base font-bold flex items-center justify-center gap-2"
            >
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
              </svg>
              Redact Document
            </button>
          </div>
        </form>

        {/* Inset Progress Bar */}
        {loading && (
          <div className="mt-6">
            <div className="neu-progress-track">
              <div
                className="neu-progress-fill"
                style={{ width: `${progressPercent}%` }}
              />
            </div>
            <div className="text-xs text-[var(--text-secondary)] text-center mt-2">
              {progressStatus}
            </div>
          </div>
        )}

        {/* Results Card */}
        {redactedResult && (
          <div className="mt-7 pt-6 border-t border-slate-200/50">
            <div className="flex items-center gap-2 text-base font-bold text-[var(--text-primary)] mb-4 font-[family-name:var(--font-nunito)]">
              <svg
                width="22"
                height="22"
                viewBox="0 0 24 24"
                fill="none"
                stroke="#22c55e"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                <polyline points="22 4 12 14.01 9 11.01" />
              </svg>
              Redaction Complete
            </div>

            <div className="grid grid-cols-2 gap-4 mb-6">
              <div className="stat-badge">
                <div className="text-xl sm:text-2xl font-extrabold text-[var(--accent)] truncate">
                  {redactedResult.subjectEntity}
                </div>
                <div className="text-xs text-[var(--text-secondary)] mt-1">Auto-Exempt Subject</div>
              </div>
              <div className="stat-badge">
                <div className="text-xl sm:text-2xl font-extrabold text-[var(--accent)]">
                  {redactedResult.piiCount}
                </div>
                <div className="text-xs text-[var(--text-secondary)] mt-1">Unique PII Redacted</div>
              </div>
            </div>

            <a
              href={redactedResult.downloadUrl}
              download={redactedResult.filename}
              className="neu-btn-secondary w-full py-3.5 text-center flex items-center justify-center gap-2 text-sm font-bold no-underline"
            >
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="7 10 12 15 17 10" />
                <line x1="12" y1="15" x2="12" y2="3" />
              </svg>
              Download Redacted Document (.docx)
            </a>
          </div>
        )}
      </div>

      <footer className="text-center text-xs text-[var(--text-muted)] mt-8">
        Soft UI Neumorphic Design System • PII Redaction Studio
      </footer>
    </div>
  );
}
