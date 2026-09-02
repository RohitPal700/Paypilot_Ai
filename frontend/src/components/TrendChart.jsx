import { formatCurrency } from "../utils/format";

/**
 * points: [{ label, value }] in chronological order.
 * Pure SVG, no external charting library.
 *
 * Three distinct cases are handled explicitly, because a line chart is
 * only a meaningful visualization when there's something to connect:
 *   - 0 points  -> "no data yet" message
 *   - 1 point   -> a single highlighted value card, not a lone unlabeled
 *                  dot on an otherwise-empty chart canvas
 *   - 2+ points -> the actual connected line/area chart, with value labels
 *                  shown directly when there are few enough points to fit
 *                  without crowding, and a hover tooltip on every point
 *                  regardless of count
 */
export default function TrendChart({ points }) {
  if (!points || points.length === 0) {
    return <div className="state-message">No data yet.</div>;
  }

  if (points.length === 1) {
    return <SinglePointTrend point={points[0]} />;
  }

  return <MultiPointTrend points={points} />;
}

function SinglePointTrend({ point }) {
  return (
    <div className="trend-single">
      <div className="trend-single-value">{formatCurrency(point.value)}</div>
      <div className="trend-single-label">{point.label}</div>
      <div className="trend-single-note">
        Only one day of data so far — the trend line will appear once
        transactions span more than one day.
      </div>
    </div>
  );
}

function MultiPointTrend({ points }) {
  const width = 560;
  const height = 180;
  const paddingX = 12;
  const paddingY = 16;
  // Extra headroom above the line so value labels don't collide with the
  // top edge of the chart when the highest point is near the max value.
  const labelHeadroom = 22;

  const values = points.map((p) => p.value);
  const max = Math.max(...values, 1);
  const min = Math.min(...values, 0);
  const range = max - min || 1;

  const plotTop = paddingY + labelHeadroom;
  const plotBottom = height - paddingY;

  const stepX = (width - paddingX * 2) / (points.length - 1);

  const coords = points.map((p, i) => {
    const x = paddingX + i * stepX;
    const y = plotBottom - ((p.value - min) / range) * (plotBottom - plotTop);
    return { x, y, ...p };
  });

  const linePath = coords
    .map((c, i) => `${i === 0 ? "M" : "L"} ${c.x.toFixed(1)} ${c.y.toFixed(1)}`)
    .join(" ");

  const areaPath = `${linePath} L ${coords[coords.length - 1].x.toFixed(1)} ${plotBottom} L ${coords[0].x.toFixed(1)} ${plotBottom} Z`;

  // Show at most ~6 x-axis date labels so dense data doesn't overlap.
  const dateLabelEvery = Math.max(1, Math.ceil(coords.length / 6));

  // Only annotate every point with its value when there's room to do so
  // without the labels overlapping each other.
  const showAllValueLabels = coords.length <= 8;

  return (
    <svg
      viewBox={`0 0 ${width} ${height + 20}`}
      className="trend-chart"
      preserveAspectRatio="xMidYMid meet"
      style={{ width: "100%", height: "auto" }}
    >
      <defs>
        <linearGradient id="trendFill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#22c55e" stopOpacity="0.35" />
          <stop offset="100%" stopColor="#22c55e" stopOpacity="0" />
        </linearGradient>
      </defs>

      <path d={areaPath} fill="url(#trendFill)" stroke="none" />
      <path d={linePath} fill="none" stroke="#22c55e" strokeWidth="2" />

      {coords.map((c) => (
        <g key={c.label}>
          <circle cx={c.x} cy={c.y} r="3" fill="#22c55e" />
          {/* Native SVG tooltip: shows the exact amount on hover for every
              point, regardless of how many points there are. No JS state,
              no extra library. */}
          <title>{`${c.label}: ${formatCurrency(c.value)}`}</title>
        </g>
      ))}

      {showAllValueLabels &&
        coords.map((c) => (
          <text
            key={`value-${c.label}`}
            x={c.x}
            y={Math.max(c.y - 10, 10)}
            fontSize="9"
            fill="#9aa0a8"
            textAnchor="middle"
          >
            {formatCurrency(c.value)}
          </text>
        ))}

      {coords.map((c, i) =>
        i % dateLabelEvery === 0 ? (
          <text
            key={`label-${c.label}`}
            x={c.x}
            y={height + 14}
            fontSize="9"
            fill="#5c626b"
            textAnchor="middle"
          >
            {c.label}
          </text>
        ) : null
      )}
    </svg>
  );
}