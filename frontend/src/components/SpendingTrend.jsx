import { useFetchOnMount } from "../hooks/useFetchOnMount";
import { getAnalyticsByDate } from "../services/api";
import { formatDateLabel } from "../utils/format";
import TrendChart from "./TrendChart";

export default function SpendingTrend() {
  const { data, loading, error } = useFetchOnMount(getAnalyticsByDate);

  return (
    <div className="card full-width-card">
      <div className="chart-title">Spending Trend</div>
      <div className="chart-subtitle">Total transaction amount per day</div>
      <div className="chart-body">
        {loading && <div className="state-message">Loading…</div>}
        {error && <div className="state-message error">Couldn't load: {error}</div>}
        {data && (
          <TrendChart
            points={data.results.map((r) => ({
              label: formatDateLabel(r.date),
              value: r.total_amount,
            }))}
          />
        )}
      </div>
    </div>
  );
}