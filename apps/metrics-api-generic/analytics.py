from db import get_connection

COUNTY_NAMES = {
    "37183": "Wake",
    "37063": "Durham",
    "37135": "Orange",
    "37101": "Johnston",
    "37037": "Chatham",
    "37069": "Franklin",
    "37077": "Granville",
    "37145": "Person",
}

# Whitelisted (table, column) pairs for trend/compare — table and column are
# string-interpolated into SQL below, so only values from this map are ever
# accepted from a query param.
TREND_METRICS = {
    "median_sale_price": ("county_market", "avg_median_sale_price"),
    "price_yoy_pct": ("county_market", "avg_price_yoy"),
    "months_of_supply": ("county_market", "avg_months_of_supply"),
    "affordability_index": ("affordability", "avg_affordability_index"),
    "market_health_score": ("market_health", "avg_market_health_score"),
}


def _rows_as_dicts(cur) -> list[dict]:
    cols = [c.name for c in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def _latest_nonnull(rows: list[dict], key: str) -> dict | None:
    """First row (rows already ordered newest-first) where `key` isn't null."""
    for r in rows:
        if r.get(key) is not None:
            return r
    return None


def _latest_with_delta(rows: list[dict], key: str) -> dict | None:
    """Latest non-null row for `key`, plus month-over-month delta against the
    next non-null value after it (tables without a precomputed *_mom column)."""
    nonnull = [r for r in rows if r.get(key) is not None]
    if not nonnull:
        return None
    latest = dict(nonnull[0])
    latest["delta"] = (nonnull[0][key] - nonnull[1][key]) if len(nonnull) > 1 else None
    return latest


def kpi_summary(county_fips: str) -> dict:
    # Different source feeds lag by different amounts, so the newest date_key
    # can be null for one metric while populated for another (e.g. sale price
    # trails months_of_supply by ~2 months). Fetch a small window per table
    # and pick the latest non-null value independently per metric, rather
    # than assuming the single newest row is complete.
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT date_key, avg_median_sale_price, avg_price_mom, avg_price_yoy,
                   avg_months_of_supply
            FROM semantic.county_market
            WHERE county_fips = %s
            ORDER BY date_key DESC LIMIT 6
            """,
            (county_fips,),
        )
        county_market = _rows_as_dicts(cur)

        cur.execute(
            """
            SELECT date_key, avg_affordability_index
            FROM semantic.affordability
            WHERE county_fips = %s
            ORDER BY date_key DESC LIMIT 6
            """,
            (county_fips,),
        )
        affordability = _rows_as_dicts(cur)

        cur.execute(
            """
            SELECT date_key, avg_market_health_score, avg_dom_score,
                   avg_sale_to_list_score, avg_supply_score, avg_momentum_score,
                   avg_affordability_score
            FROM semantic.market_health
            WHERE county_fips = %s
            ORDER BY date_key DESC LIMIT 6
            """,
            (county_fips,),
        )
        market_health = _rows_as_dicts(cur)

    return {
        "county_fips": county_fips,
        "county_name": COUNTY_NAMES.get(county_fips, county_fips),
        "median_sale_price": _latest_nonnull(county_market, "avg_median_sale_price"),
        "months_of_supply": _latest_with_delta(county_market, "avg_months_of_supply"),
        "affordability_index": _latest_with_delta(affordability, "avg_affordability_index"),
        "market_health": _latest_with_delta(market_health, "avg_market_health_score"),
    }


def trend(metric_key: str, months: int = 60) -> list[dict]:
    table, column = TREND_METRICS[metric_key]
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT county_fips, date_key, "{column}" AS value
            FROM semantic.{table}
            WHERE date_key >= (CURRENT_DATE - INTERVAL '{int(months)} months')
            ORDER BY county_fips, date_key
            """
        )
        rows = _rows_as_dicts(cur)
    for r in rows:
        r["county_name"] = COUNTY_NAMES.get(r["county_fips"], r["county_fips"])
    return rows


def compare(metric_key: str) -> list[dict]:
    table, column = TREND_METRICS[metric_key]
    with get_connection() as conn, conn.cursor() as cur:
        # Skip nulls per-metric (source feeds lag by different amounts —
        # see kpi_summary) so a stale latest month doesn't blank out the
        # comparison instead of showing the most recent real value.
        cur.execute(
            f"""
            SELECT DISTINCT ON (county_fips) county_fips, date_key, "{column}" AS value
            FROM semantic.{table}
            WHERE "{column}" IS NOT NULL
            ORDER BY county_fips, date_key DESC
            """
        )
        rows = _rows_as_dicts(cur)
    for r in rows:
        r["county_name"] = COUNTY_NAMES.get(r["county_fips"], r["county_fips"])
    rows.sort(key=lambda r: (r["value"] is None, r["value"]), reverse=True)
    return rows
