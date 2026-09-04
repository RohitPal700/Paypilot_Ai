import { useFetchOnMount } from "../hooks/useFetchOnMount";
import { getAnalyticsByStatus } from "../services/api";
import { formatNumber } from "../utils/format";
import BarList from "./BarList";

const STATUS_COLORS = {
  successful: "var(--green)",
  failed: "var(--red)",
  pending: "var(--amber)",
};

export default function StatusBreakdown({ refreshKey, statementId }) {
  const { data, loading, error } = useFetchOnMount(() => getAnalyticsByStatus(statementId), [statementId, refreshKey]);

  return (
    <div className="card">
      <div className="chart-title">Transactions by Status</div>
      <div className="chart-subtitle">Count of transactions in each status</div>
      <div className="chart-body">
        {loading && !data && <div className="state-message">Loading…</div>}
        {error && <div className="state-message error">Couldn't load: {error}</div>}
        {data && (
          <BarList
            items={[...data.results]
              .sort((a, b) => b.count - a.count)
              .map((r) => ({ label: r.status, value: r.count, status: r.status }))}
            valueFormatter={formatNumber}
            colorFor={(item) => STATUS_COLORS[item.status] || "var(--green)"}
          />
        )}
      </div>
    </div>
  );
}