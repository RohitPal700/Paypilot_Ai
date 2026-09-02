import { useFetchOnMount } from "../hooks/useFetchOnMount";
import { getAnalyticsByCategory } from "../services/api";
import { formatCurrency } from "../utils/format";
import BarList from "./BarList";

export default function CategoryBreakdown() {
  const { data, loading, error } = useFetchOnMount(getAnalyticsByCategory);

  return (
    <div className="card">
      <div className="chart-title">Spend by Category</div>
      <div className="chart-subtitle">Total transaction amount, grouped by category</div>
      <div className="chart-body">
        {loading && <div className="state-message">Loading…</div>}
        {error && <div className="state-message error">Couldn't load: {error}</div>}
        {data && (
          <BarList
            items={[...data.results]
              .sort((a, b) => b.total_amount - a.total_amount)
              .map((r) => ({ label: r.category, value: r.total_amount }))}
            valueFormatter={formatCurrency}
          />
        )}
      </div>
    </div>
  );
}