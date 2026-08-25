from dataclasses import dataclass


@dataclass(frozen=True)
class MetricViewSpec:
    short_name: str
    table: str  # Postgres table in the "semantic" schema, synced from Lakebase
    dimensions: list[str]
    measures: list[str]


REGISTRY: dict[str, MetricViewSpec] = {
    "county-market": MetricViewSpec(
        short_name="county-market",
        table="county_market",
        dimensions=["county_fips", "date_key"],
        measures=[
            "avg_median_sale_price", "avg_median_list_price", "avg_hpi_index",
            "avg_list_vs_sale_gap", "total_active_listings", "total_new_listings",
            "total_pending_listings", "pending_to_active_ratio",
            "avg_months_of_supply", "avg_days_on_market", "avg_sale_to_list_ratio",
            "avg_sold_above_list_pct", "avg_price_per_sqft", "avg_price_mom",
            "avg_price_yoy", "county_month_count",
        ],
    ),
    "affordability": MetricViewSpec(
        short_name="affordability",
        table="affordability",
        dimensions=["county_fips", "date_key"],
        measures=[
            "avg_median_sale_price", "avg_mortgage_rate", "avg_median_income",
            "avg_monthly_payment", "avg_affordability_index",
            "avg_price_to_income_ratio", "county_month_count",
        ],
    ),
    "market-health": MetricViewSpec(
        short_name="market-health",
        table="market_health",
        dimensions=["county_fips", "date_key"],
        measures=[
            "avg_days_on_market", "avg_sale_to_list_ratio", "avg_months_of_supply",
            "avg_price_yoy", "avg_affordability_index", "avg_dom_score",
            "avg_sale_to_list_score", "avg_supply_score", "avg_momentum_score",
            "avg_affordability_score", "avg_market_health_score",
            "max_market_health_score", "county_month_count",
        ],
    ),
    "supply-demand": MetricViewSpec(
        short_name="supply-demand",
        table="supply_demand",
        dimensions=["county_fips", "date_key"],
        measures=[
            "total_single_family_units", "total_multi_family_units",
            "total_units_permitted", "multi_family_share",
            "avg_county_unemployment_rate", "avg_mortgage_rate",
            "avg_median_sale_price", "total_active_listings",
            "avg_months_of_supply", "avg_price_yoy",
            "avg_national_housing_starts", "avg_nc_building_permits",
            "county_month_count",
        ],
    ),
    "zip-hotspots": MetricViewSpec(
        short_name="zip-hotspots",
        table="zip_hotspots_metrics",
        dimensions=["zip", "zip_name"],
        measures=[
            "avg_days_on_market", "total_active_listings", "price_reduction_rate",
        ],
    ),
}
