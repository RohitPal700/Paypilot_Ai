from fastapi import FastAPI

from app.api.analytics import router as analytics_router
from app.api.transactions import router as transactions_router
from app.db.mongodb import check_connection

app = FastAPI(title="PayPilot AI")

app.include_router(transactions_router)
app.include_router(analytics_router)


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