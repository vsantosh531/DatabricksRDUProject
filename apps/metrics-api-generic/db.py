import os

import psycopg2
from databricks.sdk import WorkspaceClient

_w = WorkspaceClient()

_ENDPOINT_NAME = "projects/rdu-metrics-api/branches/production/endpoints/primary"
_HOST = "ep-odd-meadow-d81r1wsi.database.us-east-2.cloud.databricks.com"
_DBNAME = "databricks_postgres"


def get_connection():
    # Deployed app: DATABRICKS_CLIENT_ID is the app's own service principal,
    # already registered as a LAKEBASE_OAUTH_V1 Postgres role. Local dev falls
    # back to the developer's own Databricks identity (email).
    user = os.environ.get("DATABRICKS_CLIENT_ID") or _w.current_user.me().user_name
    token = _w.postgres.generate_database_credential(endpoint=_ENDPOINT_NAME).token
    return psycopg2.connect(
        host=_HOST,
        port=5432,
        dbname=_DBNAME,
        user=user,
        password=token,
        sslmode="require",
    )


def run_table_query(
    table: str,
    columns: list[str],
    limit: int = 500,
) -> list[dict]:
    col_sql = ", ".join(f'"{c}"' for c in columns)
    sql_text = f'SELECT {col_sql} FROM semantic."{table}" ORDER BY 1, 2 LIMIT %s'

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(sql_text, (limit,))
        cols = [c.name for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]
