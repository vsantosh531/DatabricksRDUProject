from fastapi import APIRouter, Query

from db import run_table_query
from models import AffordabilityRow

router = APIRouter()

TABLE = "affordability"
COLUMNS = [
    "county_fips", "date_key",
    "avg_median_sale_price", "avg_mortgage_rate", "avg_median_income",
    "avg_monthly_payment", "avg_affordability_index",
    "avg_price_to_income_ratio", "county_month_count",
]


@router.get("/api/affordability", response_model=list[AffordabilityRow])
def get_affordability(limit: int = Query(default=500, le=5000)):
    return run_table_query(TABLE, COLUMNS, limit=limit)
