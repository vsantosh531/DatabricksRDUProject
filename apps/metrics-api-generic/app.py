import os

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

import analytics
from db import run_table_query
from proxy import DEDICATED_ROUTES, call_dedicated
from registry import REGISTRY

app = FastAPI(title="RDU Metrics API (generic)")

_PORTAL_HTML = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "portal.html")


@app.get("/")
def portal():
    return FileResponse(_PORTAL_HTML)


@app.get("/api/metrics")
def list_metrics():
    return [
        {
            "short_name": spec.short_name,
            "table": spec.table,
            "dimensions": spec.dimensions,
            "measures": spec.measures,
        }
        for spec in REGISTRY.values()
    ]


@app.get("/api/metrics/{view_name}")
def get_metric_view(
    view_name: str,
    dimensions: str | None = Query(default=None, description="Comma-separated dimension names"),
    measures: str | None = Query(default=None, description="Comma-separated measure names"),
    limit: int = Query(default=500, le=5000),
):
    spec = REGISTRY.get(view_name)
    if spec is None:
        raise HTTPException(status_code=404, detail=f"Unknown metric view '{view_name}'")

    dims = spec.dimensions
    if dimensions is not None:
        requested = [d.strip() for d in dimensions.split(",") if d.strip()]
        unknown = set(requested) - set(spec.dimensions)
        if unknown:
            raise HTTPException(status_code=400, detail=f"Unknown dimensions: {sorted(unknown)}")
        dims = requested

    meas = spec.measures
    if measures is not None:
        requested = [m.strip() for m in measures.split(",") if m.strip()]
        unknown = set(requested) - set(spec.measures)
        if unknown:
            raise HTTPException(status_code=400, detail=f"Unknown measures: {sorted(unknown)}")
        meas = requested

    return run_table_query(spec.table, dims + meas, limit=limit)


@app.get("/api/proxy/dedicated/{view_name}")
def proxy_dedicated(view_name: str, limit: int = Query(default=500, le=5000)):
    if view_name not in DEDICATED_ROUTES:
        raise HTTPException(status_code=404, detail=f"Unknown metric view '{view_name}'")
    try:
        return call_dedicated(view_name, limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"metrics-api-dedicated call failed: {exc}")


@app.get("/api/analytics/counties")
def list_counties():
    return [{"county_fips": k, "county_name": v} for k, v in sorted(analytics.COUNTY_NAMES.items(), key=lambda kv: kv[1])]


@app.get("/api/analytics/kpi")
def analytics_kpi(county_fips: str = Query(...)):
    if county_fips not in analytics.COUNTY_NAMES:
        raise HTTPException(status_code=404, detail=f"Unknown county_fips '{county_fips}'")
    return analytics.kpi_summary(county_fips)


@app.get("/api/analytics/trend")
def analytics_trend(
    metric: str = Query(...),
    months: int = Query(default=60, le=480),
):
    if metric not in analytics.TREND_METRICS:
        raise HTTPException(status_code=400, detail=f"Unknown metric '{metric}'")
    return analytics.trend(metric, months=months)


@app.get("/api/analytics/compare")
def analytics_compare(metric: str = Query(...)):
    if metric not in analytics.TREND_METRICS:
        raise HTTPException(status_code=400, detail=f"Unknown metric '{metric}'")
    return analytics.compare(metric)


@app.get("/health")
def health():
    return {"status": "ok"}
