import { useFetchOnMount } from "../hooks/useFetchOnMount";
import { getAnalyticsByCategory } from "../services/api";
import { formatCurrency, formatPercent } from "../utils/format";
import BarList from "./BarList";

export default function CategoryBreakdown({ refreshKey, statementId }) {
  const { data, loading, error } = useFetchOnMount(() => getAnalyticsByCategory(statementId), [statementId, refreshKey]);

  // Share of total spend for each category, computed from this same
  // section's own data (not a different endpoint's total) -- keeps the
  // percentages internally consistent with the amounts shown right next
  // to them, per the "all dashboard sections represent the same dataset"
  // requirement.
  const grandTotal = data?.results?.reduce((sum, r) => sum + r.total_amount, 0) ?? 0;

  return (
    <div className="card">
      <div className="chart-title">Where Your Money Went</div>
      <div className="chart-subtitle">Total amount and share of spend, grouped by category</div>
      <div className="chart-body">
        {loading && !data && <div className="state-message">Loading…</div>}
        {error && <div className="state-message error">Couldn't load: {error}</div>}
        {data && (
          <BarList
            items={[...data.results]
              .sort((a, b) => b.total_amount - a.total_amount)
              .map((r) => ({
                label: r.category,
                value: r.total_amount,
                subLabel: grandTotal > 0 ? formatPercent(r.total_amount / grandTotal) : undefined,
              }))}
            valueFormatter={formatCurrency}
          />
        )}
      </div>
    </div>
  );
}