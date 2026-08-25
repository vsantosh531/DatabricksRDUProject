from fastapi import APIRouter, Query

from db import run_table_query
from models import SupplyDemandRow

router = APIRouter()

TABLE = "supply_demand"
COLUMNS = [
    "county_fips", "date_key",
    "total_single_family_units", "total_multi_family_units",
    "total_units_permitted", "multi_family_share",
    "avg_county_unemployment_rate", "avg_mortgage_rate",
    "avg_median_sale_price", "total_active_listings",
    "avg_months_of_supply", "avg_price_yoy",
    "avg_national_housing_starts", "avg_nc_building_permits",
    "county_month_count",
]


@router.get("/api/supply-demand", response_model=list[SupplyDemandRow])
def get_supply_demand(limit: int = Query(default=500, le=5000)):
    return run_table_query(TABLE, COLUMNS, limit=limit)
