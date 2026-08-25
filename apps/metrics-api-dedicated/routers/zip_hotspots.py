from fastapi import APIRouter, Query

from db import run_table_query
from models import ZipHotspotRow

router = APIRouter()

TABLE = "zip_hotspots_metrics"
COLUMNS = [
    "zip", "zip_name",
    "avg_days_on_market", "total_active_listings", "price_reduction_rate",
]


@router.get("/api/zip-hotspots", response_model=list[ZipHotspotRow])
def get_zip_hotspots(limit: int = Query(default=500, le=5000)):
    return run_table_query(TABLE, COLUMNS, limit=limit)
