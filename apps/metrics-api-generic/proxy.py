import os
import time

import requests
from databricks.sdk.core import Config

_cfg = Config()

DEDICATED_APP_URL = "https://metrics-api-dedicated-7474648875270183.aws.databricksapps.com"

# short_name (registry.py) -> dedicated app's route
DEDICATED_ROUTES = {
    "county-market": "/api/county-market",
    "affordability": "/api/affordability",
    "market-health": "/api/market-health",
    "supply-demand": "/api/supply-demand",
    "zip-hotspots": "/api/zip-hotspots",
}

# Calling another Databricks App's HTTP endpoint needs an `all-apis`-scoped
# M2M token — the default token from cfg.authenticate() doesn't carry that
# scope and gets a 401. Mint one explicitly via client_credentials, same
# pattern documented in docs/metric_view_lakebase_api_execution_runbook.md
# for the Lakebase Data API.
_token_cache = {"access_token": None, "expires_at": 0}


def _get_all_apis_token() -> str:
    now = time.time()
    if _token_cache["access_token"] and now < _token_cache["expires_at"] - 60:
        return _token_cache["access_token"]

    resp = requests.post(
        f"{_cfg.host}/oidc/v1/token",
        auth=(os.environ["DATABRICKS_CLIENT_ID"], os.environ["DATABRICKS_CLIENT_SECRET"]),
        data={"grant_type": "client_credentials", "scope": "all-apis"},
        timeout=15,
    )
    resp.raise_for_status()
    body = resp.json()
    _token_cache["access_token"] = body["access_token"]
    _token_cache["expires_at"] = now + body.get("expires_in", 3600)
    return _token_cache["access_token"]


def call_dedicated(view_name: str, limit: int = 500):
    path = DEDICATED_ROUTES.get(view_name)
    if path is None:
        return None
    token = _get_all_apis_token()
    resp = requests.get(
        f"{DEDICATED_APP_URL}{path}",
        headers={"Authorization": f"Bearer {token}"},
        params={"limit": limit},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()
