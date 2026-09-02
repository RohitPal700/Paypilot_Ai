import { useState } from "react";
import { useFetchOnMount } from "../hooks/useFetchOnMount";
import { getHealthDb } from "../services/api";
import UploadStatement from "../components/UploadStatement";
import SummaryCards from "../components/SummaryCards";
import CategoryBreakdown from "../components/CategoryBreakdown";
import StatusBreakdown from "../components/StatusBreakdown";
import SpendingTrend from "../components/SpendingTrend";
import RiskPredictionForm from "../components/RiskPredictionForm";

export default function Dashboard() {
  const { data: health } = useFetchOnMount(getHealthDb);
  const isConnected = health?.database === "connected";

  // Bumped after a successful PDF import; passed to every analytics panel
  // as part of its fetch dependency array so they all refetch automatically
  // without each one needing its own bespoke refresh wiring.
  const [refreshKey, setRefreshKey] = useState(0);

  function handleImportSuccess() {
    setRefreshKey((key) => key + 1);
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="brand">
          <div className="brand-mark">PP</div>
          <div>
            <div className="brand-title">PayPilot AI</div>
            <div className="brand-subtitle">Autonomous Business Finance Agent</div>
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
          <span className="section-title">ML Risk Prediction</span>
          <span className="section-note">Trained on synthetic transaction data</span>
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