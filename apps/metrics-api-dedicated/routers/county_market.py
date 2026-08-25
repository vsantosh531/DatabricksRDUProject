from fastapi import APIRouter, Query

from db import run_table_query
from models import CountyMarketRow

router = APIRouter()

TABLE = "county_market"
COLUMNS = [
    "county_fips", "date_key",
    "avg_median_sale_price", "avg_median_list_price", "avg_hpi_index",
    "avg_list_vs_sale_gap", "total_active_listings", "total_new_listings",
    "total_pending_listings", "pending_to_active_ratio",
    "avg_months_of_supply", "avg_days_on_market", "avg_sale_to_list_ratio",
    "avg_sold_above_list_pct", "avg_price_per_sqft", "avg_price_mom",
    "avg_price_yoy", "county_month_count",
]


@router.get("/api/county-market", response_model=list[CountyMarketRow])
def get_county_market(limit: int = Query(default=500, le=5000)):
    return run_table_query(TABLE, COLUMNS, limit=limit)
