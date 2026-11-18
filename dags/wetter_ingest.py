from datetime import datetime, timedelta
from pathlib import Path

import requests
from airflow.decorators import dag, task
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook

API_URL = "https://api.open-meteo.com/v1/forecast"
FIELDS = ["temperature_2m", "relative_humidity_2m", "precipitation", "wind_speed_10m"]
CONN_ID = "warehouse"
SQL_DIR = str(Path(__file__).parent.parent / "sql")


@dag(
    dag_id="wetter_ingest",
    schedule="@daily",
    start_date=datetime(2026, 11, 1),
    catchup=True,
    max_active_runs=2,
    default_args={"retries": 2, "retry_delay": timedelta(minutes=2)},
    template_searchpath=SQL_DIR,
    tags=["wetter", "postgres"],
)
def wetter_ingest():

    @task
    def get_stations():
        hook = PostgresHook(postgres_conn_id=CONN_ID)
        rows = hook.get_records("select station_id, lat, lon from raw.stations")
        return [{"station_id": r[0], "lat": r[1], "lon": r[2]} for r in rows]

    @task
    def fetch(station, ds=None):
        params = {
            "latitude": station["lat"],
            "longitude": station["lon"],
            "hourly": ",".join(FIELDS),
            "start_date": ds,
            "end_date": ds,
            "timezone": "Europe/Berlin",
        }
        r = requests.get(API_URL, params=params, timeout=30)
        r.raise_for_status()
        hourly = r.json()["hourly"]

        rows = []
        for i, t in enumerate(hourly["time"]):
            rows.append((
                station["station_id"],
                t,
                hourly["temperature_2m"][i],
                hourly["relative_humidity_2m"][i],
                hourly["precipitation"][i],
                hourly["wind_speed_10m"][i],
            ))
        return rows

    @task
    def load(batches):
        rows = [row for b in batches for row in b]
        if not rows:
            raise ValueError("keine daten bekommen")

        hook = PostgresHook(postgres_conn_id=CONN_ID)
        conn = hook.get_conn()
        with conn, conn.cursor() as cur:
            cur.executemany(
                """
                insert into raw.weather_hourly
                    (station_id, ts, temperature, humidity, precipitation, wind_speed)
                values (%s, %s, %s, %s, %s, %s)
                on conflict (station_id, ts) do update set
                    temperature = excluded.temperature,
                    humidity = excluded.humidity,
                    precipitation = excluded.precipitation,
                    wind_speed = excluded.wind_speed,
                    loaded_at = now()
                """,
                rows,
            )
        conn.close()
        return len(rows)

    @task
    def check(n_rows, ds=None):
        hook = PostgresHook(postgres_conn_id=CONN_ID)
        n_stations = hook.get_first("select count(*) from raw.stations")[0]
        if n_rows < n_stations * 24:
            raise ValueError(f"nur {n_rows} zeilen fuer {ds}, erwartet {n_stations * 24}")

    daily = SQLExecuteQueryOperator(
        task_id="daily_agg",
        conn_id=CONN_ID,
        sql="daily_agg.sql",
    )

    stations = get_stations()
    batches = fetch.expand(station=stations)
    n = load(batches)
    check(n) >> daily


wetter_ingest()
