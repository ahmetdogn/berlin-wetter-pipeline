import os
import time

import psycopg2
from flask import Flask, render_template

app = Flask(__name__)

COLORS = [
    "#08306b", "#08519c", "#2171b5", "#4292c6", "#6baed6", "#9ecae1", "#c6dbef", "#deebf7",
    "#fee0d2", "#fcbba1", "#fc9272", "#fb6a4a", "#ef3b2c", "#cb181d", "#a50f15", "#67000d",
]

QUERY = """
select s.name, d.day, d.temp_min, d.temp_max, d.temp_avg, d.precip_sum
from mart.weather_daily d
join raw.stations s using (station_id)
order by s.name, d.day
"""

CACHE_SECONDS = 60
cache = {"time": 0, "rows": []}


def get_rows():
    conn = psycopg2.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        port=os.environ.get("DB_PORT", "5433"),
        dbname=os.environ.get("DB_NAME", "wetter"),
        user=os.environ.get("DB_USER", "wetter"),
        password=os.environ.get("DB_PASSWORD", "wetter"),
    )
    try:
        with conn.cursor() as cur:
            cur.execute(QUERY)
            return cur.fetchall()
    finally:
        conn.close()


def get_cached_rows():
    if time.time() - cache["time"] > CACHE_SECONDS:
        cache["rows"] = get_rows()
        cache["time"] = time.time()
    return cache["rows"]


@app.after_request
def security_headers(resp):
    resp.headers["Content-Security-Policy"] = "default-src 'none'; style-src 'unsafe-inline'"
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "no-referrer"
    return resp


def to_color(t, lo, hi):
    if hi == lo:
        return COLORS[len(COLORS) // 2]
    i = round((t - lo) / (hi - lo) * (len(COLORS) - 1))
    return COLORS[max(0, min(i, len(COLORS) - 1))]


@app.route("/")
def index():
    rows = get_cached_rows()
    if not rows:
        return render_template("index.html", stations=[], colors=COLORS)

    lo = min(r[4] for r in rows)
    hi = max(r[4] for r in rows)
    rain_max = max(r[5] or 0 for r in rows) or 1

    stations = {}
    for name, day, tmin, tmax, tavg, rain in rows:
        stations.setdefault(name, []).append({
            "day": day.strftime("%d.%m."),
            "tmin": tmin,
            "tmax": tmax,
            "tavg": tavg,
            "rain": rain or 0,
            "rain_h": (rain or 0) / rain_max * 18,
            "color": to_color(tavg, lo, hi),
        })

    return render_template(
        "index.html",
        stations=list(stations.items()),
        colors=COLORS,
        lo=lo,
        hi=hi,
    )
