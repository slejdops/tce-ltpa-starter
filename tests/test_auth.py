# -*- coding: utf-8 -*-
import os
from tce_app.settings import SETTINGS


def dash_url():
    return SETTINGS.servlet_url


def test_healthz(client):
    res = client.get("/healthz")
    assert res.status_code == 200
    assert res.json["status"] == "ok"


def test_whoami_with_header_token_success(client, requests_mock):
    # Mock DASH servlet response
    requests_mock.get(
        dash_url(),
        json={"username": "alice", "roles": ["NETCOOL_ADMIN", "TCE_USER"]},
        status_code=200,
    )

    res = client.get("/whoami", headers={"X-Lpta-Token": "dummy-token"})
    assert res.status_code == 200
    assert res.json["user"]["username"] == "alice"
    assert set(res.json["user"]["roles"]) == {"NETCOOL_ADMIN", "TCE_USER"}


def test_whoami_missing_token_is_401(client):
    res = client.get("/whoami")
    assert res.status_code == 401


def test_dashboard_forbidden_without_required_role(client, requests_mock):
    requests_mock.get(
        dash_url(),
        json={"username": "bob", "roles": ["TCE_USER"]},
        status_code=200,
    )

    res = client.get("/dashboard", headers={"X-Lpta-Token": "t"})
    assert res.status_code == 403


def test_dashboard_allowed_with_required_role(client, requests_mock):
    requests_mock.get(
        dash_url(),
        json={"username": "carol", "roles": ["TCE_ADMIN", "TCE_USER"]},
        status_code=200,
    )

    res = client.get("/dashboard", headers={"X-Lpta-Token": "t"})
    assert res.status_code == 200
    body = res.get_json()
    assert body["user"]["username"] == "carol"
    assert "TCE_ADMIN" in body["user"]["roles"]


def test_whoami_uses_cookie_when_header_missing(client, requests_mock):
    requests_mock.get(
        dash_url(),
        json={"username": "dave", "roles": ["TCE_USER"]},
        status_code=200,
    )

    # Set LTPA cookie on the test client
    client.set_cookie(
        server_name="localhost",
        key=os.getenv("LTPA_TOKEN_NAME", "LtpaToken2"),
        value="cookie-token",
    )

    res = client.get("/whoami")
    assert res.status_code == 200
    assert res.json["user"]["username"] == "dave"
