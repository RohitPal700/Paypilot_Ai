import { useState } from "react";
import { useFetchOnMount } from "../hooks/useFetchOnMount";
import { useActiveStatement } from "../hooks/useActiveStatement";
import { getHealthDb } from "../services/api";
import UploadStatement from "../components/UploadStatement";
import SummaryCards from "../components/SummaryCards";
import CategoryBreakdown from "../components/CategoryBreakdown";
import StatusBreakdown from "../components/StatusBreakdown";
import SpendingTrend from "../components/SpendingTrend";
import SmartInsights from "../components/SmartInsights";
import RiskPredictionForm from "../components/RiskPredictionForm";
import EmptyState from "../components/EmptyState";

export default function Dashboard() {
  const { data: health } = useFetchOnMount(getHealthDb);
  const isConnected = health?.database === "connected";

  // Bumped after a successful PDF import; passed to every analytics panel
  // as part of its fetch dependency array so they all refetch automatically
  // without each one needing its own bespoke refresh wiring.
  const [refreshKey, setRefreshKey] = useState(0);

  // Whether THIS browser has uploaded a statement -- gates the financial
  // report sections below. Without this, a fresh browser would show
  // whatever statement_import data already exists in the shared database
  // from earlier testing, instead of a clean empty state. See
  // hooks/useActiveStatement.js for why this is client-side/localStorage
  // rather than a backend concept (no auth in this project).
  const { hasActiveStatement, activate } = useActiveStatement();

  function handleImportSuccess() {
    // Any successful import response -- including an all-duplicates
    // response with imported === 0 -- means this statement's data
    // already exists in the database, so the dashboard should treat it
    // as active either way.
    activate();
    setRefreshKey((key) => key + 1);
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="brand">
          <div className="brand-mark">PP</div>
          <div>
            <div className="brand-title">PayPilot AI</div>
            <div className="brand-subtitle">Turns your payment statement into a monthly financial report</div>
          </div>
        </div>
        <div className="status-pill">
          <span className={`status-dot ${isConnected ? "ok" : "error"}`} />
          {isConnected ? "Database connected" : "Checking database…"}
        </div>
      </header>

      <section className="section">
        <UploadStatement onImportSuccess={handleImportSuccess} />
      </section>

      {!hasActiveStatement && (
        <section className="section">
          <div className="section-heading">
            <span className="section-title">Summary</span>
          </div>
          <EmptyState />
        </section>
      )}

      {hasActiveStatement && (
        <>
          <section className="section">
            <div className="section-heading">
              <span className="section-title">Summary</span>
            </div>
            <SummaryCards refreshKey={refreshKey} />
          </section>

          <section className="section">
            <div className="section-heading">
              <span className="section-title">Spending Analytics</span>
            </div>
            <div className="analytics-grid">
              <CategoryBreakdown refreshKey={refreshKey} />
              <StatusBreakdown refreshKey={refreshKey} />
              <SpendingTrend refreshKey={refreshKey} />
            </div>
          </section>

          <section className="section">
            <div className="section-heading">
              <span className="section-title">Smart Insights</span>
            </div>
            <SmartInsights refreshKey={refreshKey} />
          </section>
        </>
      )}

      <section className="section">
        <div className="section-heading">
          <span className="section-title">ML Payment Failure Risk</span>
          <span className="section-note">
            A separate ML model trained on synthetic data — not your statement analytics
          </span>
        </div>
        <RiskPredictionForm />
      </section>

      <footer className="app-footer">
        PayPilot AI — MVP dashboard. Failure-risk predictions are produced by a model
        trained on synthetic data; treat scores as illustrative, not financial advice.
      </footer>
    </div>
  );
}