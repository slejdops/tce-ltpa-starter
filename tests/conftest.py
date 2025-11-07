# -*- coding: utf-8 -*-
import os
import sys
import importlib
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


@pytest.fixture
def app(monkeypatch):
    # Configure env BEFORE importing the package so settings pick them up
    monkeypatch.setenv("FLASK_SECRET_KEY", "test-secret-key-for-testing-purposes-only-32-chars-minimum")
    monkeypatch.setenv("FLASK_DEBUG", "true")
    monkeypatch.setenv("DASH_HOST_IP", "dash.example.local")
    monkeypatch.setenv("DASH_HOST_PORT", "443")
    monkeypatch.setenv("DASH_INTEGRATION_SERVICE", "ltpa-integration/validate")
    monkeypatch.setenv("LTPA_TOKEN_NAME", "LtpaToken2")
    monkeypatch.setenv("VERIFY_TLS", "false")

    # Ensure fresh imports for settings/auth/views between tests
    for mod in [
        "tce_app.settings",
        "tce_app.rbac",
        "tce_app.auth",
        "tce_app.views",
        "tce_app",
    ]:
        if mod in sys.modules:
            del sys.modules[mod]

    tce_app = importlib.import_module("tce_app")
    flask_app = tce_app.create_app()

    yield flask_app


@pytest.fixture
def client(app):
    return app.test_client()
