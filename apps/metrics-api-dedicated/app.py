from fastapi import FastAPI

from routers import affordability, county_market, market_health, supply_demand, zip_hotspots

app = FastAPI(title="RDU Metrics API (dedicated routes)")

app.include_router(county_market.router)
app.include_router(affordability.router)
app.include_router(market_health.router)
app.include_router(supply_demand.router)
app.include_router(zip_hotspots.router)


@app.get("/health")
def health():
    return {"status": "ok"}
