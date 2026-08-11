import { useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import apiClient from "../api/client";

export default function UploadPage() {
  const [mode, setMode] = useState("upload"); // "upload" | "ticker"
  const [selectedFile, setSelectedFile] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const [ticker, setTicker] = useState("");
  const [status, setStatus] = useState(null);
  const [message, setMessage] = useState("");
  const [progress, setProgress] = useState(0);
  const fileInputRef = useRef(null);
  const navigate = useNavigate();

  function handleFileChange(e) {
    const file = e.target.files[0];
    if (file) { setSelectedFile(file); setStatus(null); }
  }

  function handleDrag(e) {
    e.preventDefault(); e.stopPropagation();
    setDragActive(e.type === "dragenter" || e.type === "dragover");
  }

  function handleDrop(e) {
    e.preventDefault(); e.stopPropagation(); setDragActive(false);
    const file = e.dataTransfer.files[0];
    if (file && file.type === "application/pdf") { setSelectedFile(file); setStatus(null); }
    else { setStatus("error"); setMessage("Only PDF files are allowed."); }
  }

  async function handleUpload() {
    if (!selectedFile) { setStatus("error"); setMessage("Please select a file first."); return; }
    if (selectedFile.type !== "application/pdf") { setStatus("error"); setMessage("Only PDF files are allowed."); return; }
    if (selectedFile.size > 20 * 1024 * 1024) { setStatus("error"); setMessage("File too large (max 20 MB)."); return; }

    const formData = new FormData();
    formData.append("file", selectedFile);
    try {
      setStatus("loading"); setMessage("Extracting financial data..."); setProgress(0);
      const progressInterval = setInterval(() => setProgress((p) => Math.min(p + Math.random() * 12, 90)), 600);
      const response = await apiClient.post("/api/analyze", formData, { headers: { "Content-Type": "multipart/form-data" } });
      clearInterval(progressInterval); setProgress(100);
      setTimeout(() => navigate("/dashboard", { state: response.data }), 300);
    } catch (error) {
      setStatus("error"); setMessage(error.response?.data?.detail || "Upload failed. Please try again."); setProgress(0);
    }
  }

  async function handleTickerSearch() {
    if (!ticker.trim()) { setStatus("error"); setMessage("Please enter a ticker symbol."); return; }
    try {
      setStatus("loading"); setMessage(`Fetching 10-K for ${ticker.toUpperCase()}...`); setProgress(0);
      const progressInterval = setInterval(() => setProgress((p) => Math.min(p + Math.random() * 8, 85)), 800);
      const response = await apiClient.get(`/api/filings/${ticker.trim()}`);
      clearInterval(progressInterval); setProgress(100);
      setTimeout(() => navigate("/dashboard", { state: response.data }), 300);
    } catch (error) {
      setStatus("error");
      setMessage(error.response?.data?.detail || `No 10-K found for "${ticker}". Try another ticker.`);
      setProgress(0);
    }
  }

  function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
  }

  return (
    <div className="upload-page">
      <div className="upload-container">
        <div className="upload-header">
          <h1>Analyze Financial Statements</h1>
          <p>Upload a 10-K filing or search by ticker to extract key financial data, compute ratios, and generate insights.</p>
        </div>

        {/* Mode tabs */}
        <div className="mode-tabs">
          <button className={`mode-tab ${mode === "upload" ? "active" : ""}`} onClick={() => { setMode("upload"); setStatus(null); }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
            Upload PDF
          </button>
          <button className={`mode-tab ${mode === "ticker" ? "active" : ""}`} onClick={() => { setMode("ticker"); setStatus(null); }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
            Search EDGAR
          </button>
        </div>

        {mode === "upload" ? (
          <>
            <div
              className={`drop-zone ${dragActive ? "drag-active" : ""} ${selectedFile ? "has-file" : ""}`}
              onDragEnter={handleDrag} onDragLeave={handleDrag} onDragOver={handleDrag} onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()} id="file-drop-zone"
            >
              <input ref={fileInputRef} type="file" accept=".pdf" onChange={handleFileChange} className="file-input-hidden" id="file-input" />
              {selectedFile ? (
                <div className="selected-file-info">
                  <div className="file-icon">
                    <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="1.5"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                  </div>
                  <p className="file-name">{selectedFile.name}</p>
                  <p className="file-size">{formatFileSize(selectedFile.size)}</p>
                  <button className="change-file-btn" onClick={(e) => { e.stopPropagation(); setSelectedFile(null); setStatus(null); }}>Change file</button>
                </div>
              ) : (
                <div className="drop-zone-content">
                  <div className="drop-icon">
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
                  </div>
                  <p className="drop-text"><strong>Drop your PDF here</strong> or click to browse</p>
                  <p className="drop-hint">Supports 10-K filings, annual reports (max 20 MB)</p>
                </div>
              )}
            </div>
            <button onClick={handleUpload} disabled={!selectedFile || status === "loading"} className="btn-analyze" id="analyze-btn">
              {status === "loading" ? (<><div className="btn-spinner" />Analyzing...</>) : (
                <><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>Analyze Report</>
              )}
            </button>
          </>
        ) : (
          <>
            <div className="ticker-search">
              <div className="ticker-input-wrapper">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" strokeWidth="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
                <input
                  type="text"
                  value={ticker}
                  onChange={(e) => { setTicker(e.target.value.toUpperCase()); setStatus(null); }}
                  onKeyDown={(e) => e.key === "Enter" && handleTickerSearch()}
                  placeholder="Enter ticker (e.g. AAPL, MSFT, GOOG)"
                  className="ticker-input"
                  id="ticker-input"
                  maxLength={10}
                />
              </div>
              <p className="ticker-hint">Searches SEC EDGAR for the company's latest 10-K filing</p>
            </div>
            <button onClick={handleTickerSearch} disabled={!ticker.trim() || status === "loading"} className="btn-analyze" id="ticker-search-btn">
              {status === "loading" ? (<><div className="btn-spinner" />Fetching...</>) : (
                <><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>Search EDGAR</>
              )}
            </button>
          </>
        )}

        {status === "loading" && (
          <div className="progress-section">
            <div className="progress-bar"><div className="progress-fill" style={{ width: `${progress}%` }} /></div>
            <p className="progress-text">{message}</p>
          </div>
        )}

        {status === "error" && (
          <div className="error-banner">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
            {message}
          </div>
        )}
      </div>
    </div>
  );
}