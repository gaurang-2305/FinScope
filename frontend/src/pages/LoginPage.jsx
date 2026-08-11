import { useAuth } from "../context/AuthContext";
import { Navigate } from "react-router-dom";

export default function LoginPage() {
  const { user, loading, login } = useAuth();

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="loading-spinner" />
      </div>
    );
  }

  if (user) {
    return <Navigate to="/" replace />;
  }

  return (
    <div className="login-page">
      {/* Animated background orbs */}
      <div className="bg-orb bg-orb-1" />
      <div className="bg-orb bg-orb-2" />
      <div className="bg-orb bg-orb-3" />

      <div className="login-card">
        <div className="login-logo">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M3 3h18v18H3V3zm2 2v14h14V5H5zm2 3h10v2H7V8zm0 4h7v2H7v-2z" fill="url(#loginGrad)"/>
            <defs>
              <linearGradient id="loginGrad" x1="3" y1="3" x2="21" y2="21">
                <stop stopColor="#6366f1"/>
                <stop offset="1" stopColor="#a78bfa"/>
              </linearGradient>
            </defs>
          </svg>
        </div>

        <h1 className="login-title">FinScope</h1>
        <p className="login-subtitle">
          AI-powered financial statement analysis.
          <br />
          Extract, validate, and explore 10-K filings in seconds.
        </p>

        <button onClick={login} className="google-btn" id="google-sign-in">
          <svg width="20" height="20" viewBox="0 0 48 48">
            <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
            <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
            <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
            <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
          </svg>
          Sign in with Google
        </button>

        <div className="login-features">
          <div className="feature-item">
            <span className="feature-icon">📊</span>
            <span>Auto-extract financial data from PDFs</span>
          </div>
          <div className="feature-item">
            <span className="feature-icon">🤖</span>
            <span>AI-powered accuracy with provenance tracking</span>
          </div>
          <div className="feature-item">
            <span className="feature-icon">🔍</span>
            <span>Search SEC EDGAR filings by ticker</span>
          </div>
        </div>
      </div>
    </div>
  );
}
