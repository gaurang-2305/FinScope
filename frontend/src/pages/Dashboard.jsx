import { useLocation, useNavigate, Link } from "react-router-dom";
import { useState } from "react";
import ChatPanel from "../components/ChatPanel";

const FIELD_LABELS = {
  total_assets: "Total Assets",
  current_assets: "Current Assets",
  total_liabilities: "Total Liabilities",
  current_liabilities: "Current Liabilities",
  total_equity: "Total Equity",
  revenue: "Revenue",
  cogs: "Cost of Goods Sold",
  operating_income: "Operating Income",
  net_income: "Net Income",
};

const RATIO_LABELS = {
  current_ratio: { label: "Current Ratio", description: "Liquidity measure", good: (v) => v >= 1 },
  debt_to_equity: { label: "Debt to Equity", description: "Leverage measure", good: (v) => v <= 2 },
  net_margin: { label: "Net Margin", description: "Profitability", good: (v) => v > 0, format: "percent" },
  roa: { label: "Return on Assets", description: "Asset efficiency", good: (v) => v > 0, format: "percent" },
  roe: { label: "Return on Equity", description: "Equity return", good: (v) => v > 0, format: "percent" },
};

function formatCurrency(value) {
  if (value == null) return "—";
  const abs = Math.abs(value);
  const sign = value < 0 ? "-" : "";
  if (abs >= 1e9) return `${sign}$${(abs / 1e9).toFixed(2)}B`;
  if (abs >= 1e6) return `${sign}$${(abs / 1e6).toFixed(2)}M`;
  if (abs >= 1e3) return `${sign}$${(abs / 1e3).toFixed(2)}K`;
  return `${sign}$${abs.toFixed(2)}`;
}

function formatRatio(value, format) {
  if (value == null) return "—";
  if (format === "percent") return `${(value * 100).toFixed(1)}%`;
  return value.toFixed(2);
}

const METHOD_LABELS = {
  regex: "Pattern Match",
  llm: "AI Extracted",
  llm_retry: "AI Re-extracted",
};

function ProvenancePopover({ provenance, onClose }) {
  if (!provenance) return null;
  return (
    <div className="provenance-popover" onClick={(e) => e.stopPropagation()}>
      <div className="provenance-header">
        <span>Source Details</span>
        <button onClick={onClose} className="provenance-close">×</button>
      </div>
      <div className="provenance-body">
        <div className="provenance-row">
          <span className="provenance-label">Method</span>
          <span className={`provenance-badge method-${provenance.extraction_method}`}>
            {METHOD_LABELS[provenance.extraction_method] || provenance.extraction_method}
          </span>
        </div>
        {provenance.page_number && (
          <div className="provenance-row">
            <span className="provenance-label">Page</span>
            <span className="provenance-value">Page {provenance.page_number}</span>
          </div>
        )}
        {provenance.confidence != null && (
          <div className="provenance-row">
            <span className="provenance-label">Confidence</span>
            <div className="confidence-bar-container">
              <div className="confidence-bar" style={{ width: `${provenance.confidence * 100}%` }}>
                <span>{Math.round(provenance.confidence * 100)}%</span>
              </div>
            </div>
          </div>
        )}
        {provenance.source_text && (
          <div className="provenance-source">
            <span className="provenance-label">Source Text</span>
            <pre className="source-text">{provenance.source_text}</pre>
          </div>
        )}
      </div>
    </div>
  );
}

export default function Dashboard() {
  const location = useLocation();
  const navigate = useNavigate();
  const data = location.state;
  const [activeProvenance, setActiveProvenance] = useState(null);

  if (!data) {
    return (
      <div className="dashboard-empty">
        <div className="empty-card">
          <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
          </svg>
          <h2>No Report Loaded</h2>
          <p>Upload a financial report to see the analysis dashboard.</p>
          <Link to="/" className="btn-primary">Upload a Report</Link>
        </div>
      </div>
    );
  }

  const { statement, ratios, provenance = {}, warnings = [] } = data;
  const balanceSheet = ["total_assets", "current_assets", "total_liabilities", "current_liabilities", "total_equity"];
  const incomeStatement = ["revenue", "cogs", "operating_income", "net_income"];
  const populatedCount = Object.values(statement).filter((v) => v != null).length;
  const totalFields = Object.keys(statement).length;

  function toggleProvenance(fieldName) {
    if (activeProvenance === fieldName) {
      setActiveProvenance(null);
    } else {
      setActiveProvenance(fieldName);
    }
  }

  function renderFieldRow(key) {
    const prov = provenance[key];
    const isLowConfidence = prov && prov.confidence != null && prov.confidence < 0.6;
    return (
      <div
        key={key}
        className={`field-row ${statement[key] == null ? "missing" : "clickable"} ${isLowConfidence ? "low-confidence" : ""}`}
        onClick={() => statement[key] != null && toggleProvenance(key)}
      >
        <span className="field-label">
          {FIELD_LABELS[key]}
          {isLowConfidence && <span className="warning-badge" title="Low confidence">⚠</span>}
          {prov && (
            <span className={`method-dot method-${prov.extraction_method}`} title={METHOD_LABELS[prov.extraction_method] || prov.extraction_method} />
          )}
        </span>
        <span className="field-value">{formatCurrency(statement[key])}</span>
        {activeProvenance === key && prov && (
          <ProvenancePopover provenance={prov} onClose={() => setActiveProvenance(null)} />
        )}
      </div>
    );
  }

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <div>
          <h1>Financial Analysis</h1>
          <p className="dashboard-subtitle">
            {data.filename || data.ticker || "Uploaded Report"} · {populatedCount}/{totalFields} fields extracted
            {data.filing_date && ` · Filed ${data.filing_date}`}
          </p>
        </div>
        <button onClick={() => navigate("/")} className="btn-secondary">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="15 18 9 12 15 6"/></svg>
          New Analysis
        </button>
      </div>

      {/* Warnings */}
      {warnings.length > 0 && (
        <div className="warnings-panel">
          {warnings.map((w, i) => (
            <div key={i} className="warning-item">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
                <line x1="12" y1="9" x2="12" y2="13"/>
                <line x1="12" y1="17" x2="12.01" y2="17"/>
              </svg>
              <span>{w}</span>
            </div>
          ))}
        </div>
      )}

      {/* Coverage bar */}
      <div className="coverage-bar">
        <div className="coverage-label">
          <span>Extraction Coverage</span>
          <span className="coverage-pct">{Math.round((populatedCount / totalFields) * 100)}%</span>
        </div>
        <div className="coverage-track">
          <div className="coverage-fill" style={{ width: `${(populatedCount / totalFields) * 100}%` }} />
        </div>
      </div>

      <div className="dashboard-grid">
        <div className="data-card">
          <div className="card-header">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="2"><rect x="2" y="3" width="20" height="18" rx="2"/><line x1="2" y1="9" x2="22" y2="9"/><line x1="12" y1="9" x2="12" y2="21"/></svg>
            <h2>Balance Sheet</h2>
          </div>
          <p className="card-hint">Click any value to see its source</p>
          <div className="field-list">
            {balanceSheet.map(renderFieldRow)}
          </div>
        </div>

        <div className="data-card">
          <div className="card-header">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
            <h2>Income Statement</h2>
          </div>
          <p className="card-hint">Click any value to see its source</p>
          <div className="field-list">
            {incomeStatement.map(renderFieldRow)}
          </div>
        </div>

        <div className="data-card ratios-card">
          <div className="card-header">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="2"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
            <h2>Financial Ratios</h2>
          </div>
          <div className="ratios-grid">
            {Object.entries(RATIO_LABELS).map(([key, meta]) => {
              const val = ratios[key];
              const isGood = val != null && meta.good(val);
              return (
                <div key={key} className="ratio-tile">
                  <span className="ratio-value-lg">{formatRatio(val, meta.format)}</span>
                  <span className="ratio-label">{meta.label}</span>
                  <span className="ratio-desc">{meta.description}</span>
                  {val != null && (
                    <span className={`ratio-badge ${isGood ? "good" : "warn"}`}>
                      {isGood ? "✓ Healthy" : "⚠ Review"}
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Chat Panel */}
      {data.report_id && <ChatPanel reportId={data.report_id} />}
    </div>
  );
}