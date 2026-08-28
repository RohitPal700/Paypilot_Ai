"""
Unit tests for app/ml/model_loader.py -- the singleton that loads the
persisted joblib Pipeline once and caches it.

These tests import ONLY app.ml.model_loader, not app.main or anything
touching FastAPI/MongoDB -- model_loader.py has no such dependency, so
this is a true isolated unit test, independent of any database.

Because the module keeps its cache in module-level globals, each test
resets that state first (via the autouse fixture below) so tests don't
leak state into each other regardless of run order.
"""

import pytest

import app.ml.model_loader as model_loader


@pytest.fixture(autouse=True)
def reset_model_cache():
    """Ensure every test starts and ends with a clean, unloaded cache."""
    model_loader._cached_pipeline = None
    model_loader._load_error = None
    yield
    model_loader._cached_pipeline = None
    model_loader._load_error = None


def test_get_model_loads_a_usable_pipeline():
    model = model_loader.get_model()
    assert hasattr(model, "predict_proba")
    assert hasattr(model, "predict")


def test_get_model_is_cached_not_reloaded_on_second_call():
    first = model_loader.get_model()
    second = model_loader.get_model()
    assert first is second  # same object in memory, not a fresh joblib.load


def test_get_model_raises_clean_error_when_artifact_missing(monkeypatch):
    def _boom(path):
        raise FileNotFoundError(f"no such file: {path}")

    monkeypatch.setattr(model_loader.joblib, "load", _boom)

    with pytest.raises(model_loader.ModelLoadError):
        model_loader.get_model()


def test_get_model_error_message_does_not_leak_internal_details(monkeypatch):
    def _boom(path):
        raise FileNotFoundError(f"no such file: {path}")

    monkeypatch.setattr(model_loader.joblib, "load", _boom)

    with pytest.raises(model_loader.ModelLoadError) as exc_info:
        model_loader.get_model()

    # The safe, generic message -- not the raw file path or exception text.
    assert str(exc_info.value) == "Failure-risk model is not available."


def test_get_model_does_not_retry_joblib_load_after_a_failure(monkeypatch):
    call_count = {"n": 0}

    def _boom(path):
        call_count["n"] += 1
        raise FileNotFoundError("no such file")

    monkeypatch.setattr(model_loader.joblib, "load", _boom)

    with pytest.raises(model_loader.ModelLoadError):
        model_loader.get_model()
    with pytest.raises(model_loader.ModelLoadError):
        model_loader.get_model()

    assert call_count["n"] == 1  # cached the failure, didn't retry on every call