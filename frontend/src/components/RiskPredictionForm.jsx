import { useState } from "react";
import { predictRisk } from "../services/api";
import { dayOfWeekName, formatPercent } from "../utils/format";

// Mirrors the value pools used by the backend's synthetic data generators
// (app/utils/synthetic_data.py, app/ml/synthetic_ml_data.py) so predictions
// are made with values the model actually saw during training, rather than
// arbitrary free text the encoder has never encountered.
const MERCHANTS = [
  "merchant_bluewave",
  "merchant_urbancart",
  "merchant_freshbite",
  "merchant_techhive",
  "merchant_greenleaf",
  "merchant_swiftgear",
  "merchant_daily_grind_cafe",
  "merchant_pixel_studio",
];

const CURRENCIES = ["USD", "INR", "EUR"];
const TRANSACTION_TYPES = ["payment", "refund", "chargeback", "expense"];
const PAYMENT_METHODS = ["card", "upi", "netbanking", "wallet", "bank_transfer"];
const CATEGORIES = [
  "groceries",
  "electronics",
  "software_subscription",
  "utilities",
  "travel",
  "food_delivery",
  "office_supplies",
  "marketing",
];

const INITIAL_FORM = {
  merchant_id: MERCHANTS[0],
  amount: 250,
  currency: "USD",
  transaction_type: "payment",
  payment_method: "card",
  category: "groceries",
  hour: 14,
  day_of_week: 1,
};

export default function RiskPredictionForm() {
  const [form, setForm] = useState(INITIAL_FORM);
  const [result, setResult] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  function updateField(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    setResult(null);

    try {
      const payload = {
        ...form,
        amount: Number(form.amount),
        hour: Number(form.hour),
        day_of_week: Number(form.day_of_week),
      };
      const response = await predictRisk(payload);
      setResult(response);
    } catch (err) {
      setError(err.message || "Prediction failed.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="ml-grid">
      <div className="card">
        <div className="chart-title">Predict Failure Risk</div>
        <div className="chart-subtitle">
          Enter a hypothetical transaction to get a failure-risk score
        </div>

        <form onSubmit={handleSubmit}>
          <div className="form-grid">
            <div className="form-field">
              <label htmlFor="merchant_id">Merchant</label>
              <select
                id="merchant_id"
                value={form.merchant_id}
                onChange={(e) => updateField("merchant_id", e.target.value)}
              >
                {MERCHANTS.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-field">
              <label htmlFor="amount">Amount</label>
              <input
                id="amount"
                type="number"
                min="0.01"
                step="0.01"
                value={form.amount}
                onChange={(e) => updateField("amount", e.target.value)}
                required
              />
            </div>

            <div className="form-field">
              <label htmlFor="currency">Currency</label>
              <select
                id="currency"
                value={form.currency}
                onChange={(e) => updateField("currency", e.target.value)}
              >
                {CURRENCIES.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-field">
              <label htmlFor="transaction_type">Transaction Type</label>
              <select
                id="transaction_type"
                value={form.transaction_type}
                onChange={(e) => updateField("transaction_type", e.target.value)}
              >
                {TRANSACTION_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-field">
              <label htmlFor="payment_method">Payment Method</label>
              <select
                id="payment_method"
                value={form.payment_method}
                onChange={(e) => updateField("payment_method", e.target.value)}
              >
                {PAYMENT_METHODS.map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-field">
              <label htmlFor="category">Category</label>
              <select
                id="category"
                value={form.category}
                onChange={(e) => updateField("category", e.target.value)}
              >
                {CATEGORIES.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-field">
              <label htmlFor="hour">Hour of Day (0–23)</label>
              <input
                id="hour"
                type="number"
                min="0"
                max="23"
                value={form.hour}
                onChange={(e) => updateField("hour", e.target.value)}
                required
              />
            </div>

            <div className="form-field">
              <label htmlFor="day_of_week">Day of Week</label>
              <select
                id="day_of_week"
                value={form.day_of_week}
                onChange={(e) => updateField("day_of_week", Number(e.target.value))}
              >
                {[0, 1, 2, 3, 4, 5, 6].map((d) => (
                  <option key={d} value={d}>
                    {dayOfWeekName(d)}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <button type="submit" className="submit-button" disabled={submitting}>
            {submitting ? "Predicting…" : "Predict Risk"}
          </button>
        </form>
      </div>

      <div className="card">
        <div className="chart-title">Result</div>
        <div className="chart-subtitle">Model output for the transaction above</div>
        <RiskResult result={result} error={error} submitting={submitting} />
      </div>
    </div>
  );
}

function RiskResult({ result, error, submitting }) {
  if (submitting) {
    return (
      <div className="risk-result">
        <div className="risk-placeholder">Running prediction…</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="risk-result">
        <div className="state-message error">{error}</div>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="risk-result">
        <div className="risk-placeholder">
          Fill in the form and submit to see a failure-risk prediction.
        </div>
      </div>
    );
  }

  return (
    <div className="risk-result">
      <div className="risk-probability">{formatPercent(result.failure_probability)}</div>
      <span className={`risk-tier-badge risk-${result.risk_tier}`}>
        {result.risk_tier} risk
      </span>
    </div>
  );
}