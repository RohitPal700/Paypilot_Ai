import { useFetchOnMount } from "../hooks/useFetchOnMount";
import { getAnalyticsSummary } from "../services/api";
import { formatCurrency, formatNumber } from "../utils/format";

export default function SummaryCards({ refreshKey }) {
  const { data, loading, error } = useFetchOnMount(getAnalyticsSummary, [refreshKey]);

  // On the very first load there's nothing to show yet -- block on it.
  // On a refresh (e.g. after a PDF import), keep showing the last known
  // summary instead of blanking the whole panel while the new data loads.
  if (loading && !data) {
    return <div className="state-message">Loading summary…</div>;
  }

  if (error) {
    return <div className="state-message error">Couldn't load summary: {error}</div>;
  }

  const cards = [
    {
      label: "Total Transactions",
      value: formatNumber(data.total_transactions),
      accent: "green",
    },
    {
      label: "Successful Amount",
      value: formatCurrency(data.total_successful_amount),
      accent: "green",
      valueClass: "accent-green",
    },
    {
      label: "Failed Transactions",
      value: formatNumber(data.total_failed_count),
      accent: "red",
      valueClass: "accent-red",
    },
    {
      label: "Refund Amount",
      value: formatCurrency(data.total_refund_amount),
      accent: "amber",
    },
  ];

  return (
    <div className="summary-grid">
      {cards.map((card) => (
        <div
          key={card.label}
          className="summary-card"
          style={{ "--accent-color": `var(--${card.accent})` }}
        >
          <span className="summary-label">{card.label}</span>
          <span className={`summary-value ${card.valueClass || ""}`}>{card.value}</span>
        </div>
      ))}
    </div>
  );
}