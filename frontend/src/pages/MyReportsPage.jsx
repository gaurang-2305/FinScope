import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import apiClient from "../api/client";

export default function MyReportsPage() {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    fetchReports();
  }, []);

  async function fetchReports() {
    try {
      const res = await apiClient.get("/api/reports");
      setReports(res.data);
    } catch (err) {
      setError("Failed to load reports.");
    } finally {
      setLoading(false);
    }
  }

  async function openReport(reportId) {
    try {
      const res = await apiClient.get(`/api/reports/${reportId}`);
      navigate("/dashboard", { state: res.data });
    } catch {
      setError("Failed to load report details.");
    }
  }

  function formatDate(iso) {
    if (!iso) return "";
    const d = new Date(iso);
    return d.toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="loading-spinner" />
        <p>Loading reports...</p>
      </div>
    );
  }

  return (
    <div className="reports-page">
      <div className="reports-container">
        <div className="reports-header">
          <h1>My Reports</h1>
          <p>Your previously analyzed financial statements</p>
        </div>

        {error && (
          <div className="error-banner">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10"/>
              <line x1="15" y1="9" x2="9" y2="15"/>
              <line x1="9" y1="9" x2="15" y2="15"/>
            </svg>
            {error}
          </div>
        )}

        {reports.length === 0 ? (
          <div className="empty-reports">
            <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" strokeWidth="1">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
            </svg>
            <h2>No reports yet</h2>
            <p>Upload your first financial report to get started.</p>
            <button onClick={() => navigate("/")} className="btn-primary">
              Upload a Report
            </button>
          </div>
        ) : (
          <div className="reports-list">
            {reports.map((report) => (
              <button
                key={report.id}
                className="report-card"
                onClick={() => openReport(report.id)}
              >
                <div className="report-icon">
                  {report.source_type === "edgar" ? (
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="2">
                      <circle cx="11" cy="11" r="8"/>
                      <line x1="21" y1="21" x2="16.65" y2="16.65"/>
                    </svg>
                  ) : (
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="2">
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                      <polyline points="14 2 14 8 20 8"/>
                    </svg>
                  )}
                </div>
                <div className="report-info">
                  <span className="report-name">
                    {report.ticker
                      ? `${report.ticker} — 10-K`
                      : report.filename || "Uploaded Report"}
                  </span>
                  <span className="report-date">{formatDate(report.created_at)}</span>
                </div>
                <div className="report-badge">
                  {report.source_type === "edgar" ? "EDGAR" : "Upload"}
                </div>
                <svg className="report-chevron" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="9 18 15 12 9 6"/>
                </svg>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
