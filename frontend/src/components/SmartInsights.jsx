import { useFetchOnMount } from "../hooks/useFetchOnMount";
import {
  getAnalyticsByCategory,
  getAnalyticsByDate,
  getAnalyticsByStatus,
} from "../services/api";
import { formatCurrency, formatPercent } from "../utils/format";

/**
 * Smart Insights: short, plain-language callouts summarizing the
 * uploaded statement. Every insight below is computed directly from
 * the same backend analytics endpoints the rest of the dashboard
 * already uses (by-category, by-status, by-date) -- nothing here is
 * hardcoded, guessed, or produced by a model. If a signal isn't
 * meaningful (e.g. too few days to talk about a trend, or there's no
 * category data yet), that insight is simply omitted rather than
 * invented.
 */

// Only worth calling out as a trend if the swing between the first and
// second half of the statement period is at least this large -- avoids
// reporting noise as if it were a meaningful pattern.
const TREND_SIGNIFICANCE_THRESHOLD = 0.1; // 10%

function buildInsights({ categoryResults, statusResults, dateResults }) {
  const insights = [];

  // 1. Largest spending category, and average transaction size -- both
  // computed from the SAME category totals shown in "Where Your Money
  // Went" just above, so the numbers stay consistent with what the user
  // already sees on screen.
  if (categoryResults && categoryResults.length > 0) {
    const totalAmount = categoryResults.reduce((sum, r) => sum + r.total_amount, 0);
    const totalCount = categoryResults.reduce((sum, r) => sum + r.count, 0);

    const topCategory = [...categoryResults].sort((a, b) => b.total_amount - a.total_amount)[0];
    if (totalAmount > 0) {
      const share = topCategory.total_amount / totalAmount;
      insights.push({
        icon: "💡",
        text: `${topCategory.category} is your largest spending category at ${formatCurrency(
          topCategory.total_amount
        )} (${formatPercent(share)} of total).`,
      });
    }

    if (totalCount > 0) {
      insights.push({
        icon: "💰",
        text: `Your average transaction was ${formatCurrency(totalAmount / totalCount)}.`,
      });
    }
  }

  // 2. Failed payments -- explicitly says "zero" rather than staying
  // silent, per the requirement that a clean statement should be stated
  // as such, not just omitted.
  if (statusResults) {
    const failedEntry = statusResults.find((r) => r.status === "failed");
    const failedCount = failedEntry?.count ?? 0;
    insights.push(
      failedCount > 0
        ? {
            icon: "⚠️",
            text: `You had ${failedCount} failed payment${failedCount === 1 ? "" : "s"} in this statement.`,
          }
        : {
            icon: "✅",
            text: "No failed payments in this statement — every transaction went through.",
          }
    );
  }

  // 3. Spending trend -- compares the daily average of the first half of
  // the statement period against the second half. Needs at least 4 days
  // of data for "first half vs second half" to mean anything; below that
  // it's omitted entirely rather than describing noise as a trend.
  if (dateResults && dateResults.length >= 4) {
    const sorted = [...dateResults].sort((a, b) => (a.date < b.date ? -1 : 1));
    const midpoint = Math.floor(sorted.length / 2);
    const firstHalf = sorted.slice(0, midpoint);
    const secondHalf = sorted.slice(midpoint);

    const avg = (rows) => rows.reduce((sum, r) => sum + r.total_amount, 0) / rows.length;
    const firstAvg = avg(firstHalf);
    const secondAvg = avg(secondHalf);

    if (firstAvg > 0) {
      const change = (secondAvg - firstAvg) / firstAvg;
      if (Math.abs(change) >= TREND_SIGNIFICANCE_THRESHOLD) {
        insights.push({
          icon: change > 0 ? "📈" : "📉",
          text: `Your daily spending ${change > 0 ? "increased" : "decreased"} by ${formatPercent(
            Math.abs(change)
          )} during the second half of the statement period.`,
        });
      }
    }
  }

  return insights;
}

export default function SmartInsights({ refreshKey }) {
  const category = useFetchOnMount(getAnalyticsByCategory, [refreshKey]);
  const status = useFetchOnMount(getAnalyticsByStatus, [refreshKey]);
  const date = useFetchOnMount(getAnalyticsByDate, [refreshKey]);

  const loading = category.loading || status.loading || date.loading;
  const error = category.error || status.error || date.error;
  const ready = category.data && status.data && date.data;

  const insights = ready
    ? buildInsights({
        categoryResults: category.data.results,
        statusResults: status.data.results,
        dateResults: date.data.results,
      })
    : [];

  return (
    <div className="card full-width-card">
      <div className="chart-title">Smart Insights</div>
      <div className="chart-subtitle">Automatically derived from your uploaded statement</div>
      <div className="chart-body">
        {loading && !ready && <div className="state-message">Loading…</div>}
        {error && <div className="state-message error">Couldn't load insights: {error}</div>}
        {ready && insights.length === 0 && (
          <div className="state-message">
            Not enough data yet — upload a statement to see insights here.
          </div>
        )}
        {ready && insights.length > 0 && (
          <ul className="insight-list">
            {insights.map((insight, i) => (
              <li className="insight-item" key={i}>
                <span className="insight-icon" aria-hidden="true">
                  {insight.icon}
                </span>
                <span className="insight-text">{insight.text}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}