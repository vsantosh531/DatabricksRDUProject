from fastapi import APIRouter, Query

from db import run_table_query
from models import MarketHealthRow

router = APIRouter()

TABLE = "market_health"
COLUMNS = [
    "county_fips", "date_key",
    "avg_days_on_market", "avg_sale_to_list_ratio", "avg_months_of_supply",
    "avg_price_yoy", "avg_affordability_index", "avg_dom_score",
    "avg_sale_to_list_score", "avg_supply_score", "avg_momentum_score",
    "avg_affordability_score", "avg_market_health_score",
    "max_market_health_score", "county_month_count",
]


@router.get("/api/market-health", response_model=list[MarketHealthRow])
def get_market_health(limit: int = Query(default=500, le=5000)):
    return run_table_query(TABLE, COLUMNS, limit=limit)
