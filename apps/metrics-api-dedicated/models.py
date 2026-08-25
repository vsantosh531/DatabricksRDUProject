from datetime import date

from pydantic import BaseModel


class CountyMarketRow(BaseModel):
    county_fips: str
    date_key: date
    avg_median_sale_price: float | None = None
    avg_median_list_price: float | None = None
    avg_hpi_index: float | None = None
    avg_list_vs_sale_gap: float | None = None
    total_active_listings: int | None = None
    total_new_listings: int | None = None
    total_pending_listings: int | None = None
    pending_to_active_ratio: float | None = None
    avg_months_of_supply: float | None = None
    avg_days_on_market: float | None = None
    avg_sale_to_list_ratio: float | None = None
    avg_sold_above_list_pct: float | None = None
    avg_price_per_sqft: float | None = None
    avg_price_mom: float | None = None
    avg_price_yoy: float | None = None
    county_month_count: int


class AffordabilityRow(BaseModel):
    county_fips: str
    date_key: date
    avg_median_sale_price: float | None = None
    avg_mortgage_rate: float | None = None
    avg_median_income: float | None = None
    avg_monthly_payment: float | None = None
    avg_affordability_index: float | None = None
    avg_price_to_income_ratio: float | None = None
    county_month_count: int


class MarketHealthRow(BaseModel):
    county_fips: str
    date_key: date
    avg_days_on_market: float | None = None
    avg_sale_to_list_ratio: float | None = None
    avg_months_of_supply: float | None = None
    avg_price_yoy: float | None = None
    avg_affordability_index: float | None = None
    avg_dom_score: float | None = None
    avg_sale_to_list_score: float | None = None
    avg_supply_score: float | None = None
    avg_momentum_score: float | None = None
    avg_affordability_score: float | None = None
    avg_market_health_score: float | None = None
    max_market_health_score: float | None = None
    county_month_count: int


class SupplyDemandRow(BaseModel):
    county_fips: str
    date_key: date
    total_single_family_units: int | None = None
    total_multi_family_units: int | None = None
    total_units_permitted: int | None = None
    multi_family_share: float | None = None
    avg_county_unemployment_rate: float | None = None
    avg_mortgage_rate: float | None = None
    avg_median_sale_price: float | None = None
    total_active_listings: int | None = None
    avg_months_of_supply: float | None = None
    avg_price_yoy: float | None = None
    avg_national_housing_starts: float | None = None
    avg_nc_building_permits: float | None = None
    county_month_count: int


class ZipHotspotRow(BaseModel):
    zip: str
    zip_name: str | None = None
    avg_days_on_market: float | None = None
    total_active_listings: int | None = None
    price_reduction_rate: float | None = None
