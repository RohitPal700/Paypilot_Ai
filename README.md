# PayPilot AI

PayPilot AI turns a PhonePe / Paytm / Google Pay monthly statement PDF into
an automatic financial report: where your money went, how your spending
changed over the month, your payment success/failure status, and an
ML-based payment failure-risk estimator.

## How it works

```
Upload statement PDF
        │
        ▼
Parse transactions (dates, amounts, merchants)
        │
        ▼
Deterministic category classification
        │
        ▼
Store in MongoDB (tagged as real statement data)
        │
        ▼
Analytics aggregation (spend, categories, status, daily trend)
        │
        ▼
Dashboard: Summary, Where Your Money Went, Payment Status,
           Spending Trend, Smart Insights
```

A separate, clearly-labeled ML model (trained on synthetic data, not on
your uploaded statement) estimates failure risk for a hypothetical
transaction you describe manually — this is illustrative decision support,
not a claim of certified accuracy, and it never touches your real
statement's numbers.

## Tech Stack

- **Frontend:** React (Vite), plain CSS, no external chart library
- **Backend:** FastAPI (Python)
- **Database:** MongoDB
- **ML:** scikit-learn (Logistic Regression pipeline), trained on a
  synthetic dataset designed with realistic, non-trivial failure patterns
- **PDF parsing:** pdfplumber, heuristic regex-based line parser

## Project Structure

```
paypilot-ai/
├── backend/
│   ├── app/
│   │   ├── api/          # transactions, analytics, import, ml routers
│   │   ├── db/            # MongoDB connection + indexes
│   │   ├── ml/             # training, model artifacts, risk policy
│   │   ├── schemas/       # Pydantic request/response models
│   │   ├── services/      # business logic (DB access, PDF parsing, ML)
│   │   └── utils/         # synthetic demo-data generator
│   └── tests/             # pytest suite
├── frontend/
│   └── src/
│       ├── components/    # dashboard panels
│       ├── hooks/
│       ├── pages/
│       ├── services/       # API client
│       └── utils/          # formatting helpers
└── data/                  # ML training dataset
```

## Running locally

### Backend

```
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# add MONGODB_URI and MONGODB_DB_NAME to backend/.env
uvicorn app.main:app --reload
```

### Tests

```
cd backend
source .venv/bin/activate
PYTHONPATH=. pytest tests/ -v
```

### Frontend

```
cd frontend
npm install
npm run dev    # starts on http://localhost:5173, expects backend on :8000
npm run build  # production build
```

## Demo vs. real data

`POST /api/transactions/seed` inserts ~50 synthetic transactions for local
development. These are tagged internally as demo data and are excluded
from every analytics endpoint the dashboard reads from — uploading a real
statement always produces a report of that statement, never a mix of real
and demo transactions.

## Known limitations

- The PDF parser is a best-effort, regex-based heuristic for
  PhonePe/Paytm/GPay-style statement layouts, not an officially certified
  parser for any provider's export format.
- Category classification is a deterministic keyword-based fallback, not
  an AI classifier — financial totals are never sent to a model.
- The failure-risk model is trained entirely on synthetic data; treat its
  output as illustrative, not as financial advice or a certified risk
  score.
- Multi-currency statements are summed together in the analytics endpoints
  without currency-aware separation; the dashboard formats all amounts as
  INR, matching the primary use case (Indian UPI statements).
