"""
Loads the persisted failure-risk Pipeline exactly once and caches it in
memory, so the (relatively expensive) joblib deserialization only happens
a single time -- not once per API request.

This module deliberately knows nothing about FastAPI. It raises a plain
ModelLoadError on failure; the API layer (app/api/ml.py) is responsible for
turning that into a clean HTTP response without leaking a traceback.
"""

import os

import joblib

_ARTIFACT_PATH = os.path.join(
    os.path.dirname(__file__), "artifacts", "failure_risk_model.joblib"
)

# Module-level cache -- populated on first successful load, reused after.
_cached_pipeline = None
_load_error: Exception | None = None


class ModelLoadError(Exception):
    """Raised when the persisted model artifact cannot be loaded."""


def get_model():
    """
    Return the cached Pipeline, loading it from disk on first call only.
    Raises ModelLoadError (with a safe, non-leaky message) if the artifact
    is missing or fails to load -- the exception is never re-raised as the
    raw underlying exception, so callers never see a raw file path or
    library-internal traceback.
    """
    global _cached_pipeline, _load_error

    if _cached_pipeline is not None:
        return _cached_pipeline

    if _load_error is not None:
        # A previous attempt already failed -- don't keep retrying/logging
        # the same failure on every request.
        raise ModelLoadError("Failure-risk model is not available.") from _load_error

    try:
        _cached_pipeline = joblib.load(_ARTIFACT_PATH)
        return _cached_pipeline
    except Exception as exc:  # noqa: BLE001 -- intentionally broad, converted below
        _load_error = exc
        raise ModelLoadError("Failure-risk model is not available.") from exc