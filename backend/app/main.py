from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.analytics import router as analytics_router
from app.api.import_pdf import router as import_router
from app.api.ml import router as ml_router
from app.api.transactions import router as transactions_router
from app.db.mongodb import check_connection

app = FastAPI(title="PayPilot AI")

# Minimum CORS config so the separately-running frontend (Vite dev server,
# default port 5173) can call this API. Restricted to local dev origins
# only -- this is not a production CORS policy.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(transactions_router)
app.include_router(analytics_router)
app.include_router(ml_router)
app.include_router(import_router)


@app.get("/")
def read_root():
    return {"message": "PayPilot AI Backend is running"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/health/db")
def health_check_db():
    is_connected = check_connection()
    return {"database": "connected" if is_connected else "disconnected"}