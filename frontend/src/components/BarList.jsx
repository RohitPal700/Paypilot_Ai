/**
 * items: [{ label, value }]
 * valueFormatter: (value) => string, for the number shown next to each bar
 * colorFor: optional (item) => css color, defaults to the theme green
 */
export default function BarList({ items, valueFormatter = String, colorFor }) {
  if (!items || items.length === 0) {
    return <div className="state-message">No data yet.</div>;
  }

  const max = Math.max(...items.map((i) => i.value), 1);

  return (
    <div className="bar-chart">
      {items.map((item) => {
        const widthPercent = Math.max((item.value / max) * 100, 2);
        const color = colorFor ? colorFor(item) : undefined;
        return (
          <div className="bar-chart-row" key={item.label}>
            <span className="bar-chart-label" title={item.label}>
              {item.label}
            </span>
            <span className="bar-chart-track">
              <span
                className="bar-chart-fill"
                style={{ width: `${widthPercent}%`, ...(color ? { background: color } : {}) }}
              />
            </span>
            <span className="bar-chart-value">{valueFormatter(item.value)}</span>
          </div>
        );
      })}
    </div>
  );
}