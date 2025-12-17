import os
import uuid
from datetime import datetime, timezone

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from azure.cosmos import CosmosClient, exceptions
from fastapi.staticfiles import StaticFiles
from pathlib import Path


app = FastAPI()

BASE_DIR = Path(__file__).resolve().parent

app.mount(
    "/static",
    StaticFiles(directory=BASE_DIR / "static"),
    name="static",
)


# ===== Cosmos DB =====
COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT")
COSMOS_KEY = os.getenv("COSMOS_KEY")

DB_NAME = "appdb"
CONTAINER_NAME = "jsonfiles"

client = CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)
db = client.get_database_client(DB_NAME)
container = db.get_container_client(CONTAINER_NAME)

# ===== Bukovel + Open-Meteo =====
BUKOVEL_LAT = 48.360278
BUKOVEL_LON = 24.392222
BUKOVEL_TZ = "Europe/Kyiv"

# коди "сніг" по weathercode
SNOW_CODES = {71, 73, 75, 77, 85, 86}


@app.get("/", response_class=HTMLResponse)
def index():
    # супер-проста сторінка: кнопка + місце для тексту
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.post("/refresh")
def refresh_weather():
    # 1) тягнемо погоду з Open-Meteo
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={BUKOVEL_LAT}&longitude={BUKOVEL_LON}"
        f"&current_weather=true&timezone={BUKOVEL_TZ}"
    )

    try:
        r = httpx.get(url, timeout=15.0)
        r.raise_for_status()
        payload = r.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Weather API error: {e}")

    current = payload.get("current_weather") or {}
    weathercode = current.get("weathercode")
    time_str = current.get("time")

    # 2) визначаємо сніг
    is_snowing = (weathercode in SNOW_CODES)

    # 3) записуємо в Cosmos DB
    doc_id = str(uuid.uuid4())
    now_iso = datetime.now(timezone.utc).isoformat()

    doc = {
        "id": doc_id,
        "pk": "bukovel",  # partition key (стабільний)
        "type": "weather_check",
        "created_at_utc": now_iso,
        "bukovel": {"lat": BUKOVEL_LAT, "lon": BUKOVEL_LON},
        "result": {
            "is_snowing": is_snowing,
            "weathercode": weathercode,
            "time": time_str,
        },
        "raw": payload,  # щоб було видно, що прийшло з API (можеш прибрати)
    }

    try:
        container.create_item(body=doc)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB write error: {e}")

    # 4) повертаємо результат фронтенду
    return {
        "id": doc_id,
        "pk": "bukovel",
        "is_snowing": is_snowing,
        "weathercode": weathercode,
        "time": time_str,
    }


@app.get("/forecast")
def forecast_14d():
    # Open-Meteo daily forecast for 14 days
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={BUKOVEL_LAT}&longitude={BUKOVEL_LON}"
        f"&daily=weathercode"
        f"&forecast_days=14"
        f"&timezone={BUKOVEL_TZ}"
    )

    try:
        r = httpx.get(url, timeout=15.0)
        r.raise_for_status()
        payload = r.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Forecast API error: {e}")

    daily = payload.get("daily") or {}
    dates = daily.get("time") or []
    codes = daily.get("weathercode") or []

    first_snow_date = None
    for d, c in zip(dates, codes):
        if c in SNOW_CODES:
            first_snow_date = d
            break

    # (опційно) запис в Cosmos DB
    doc_id = str(uuid.uuid4())
    now_iso = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": doc_id,
        "pk": "bukovel",
        "type": "forecast_14d",
        "created_at_utc": now_iso,
        "result": {
            "first_snow_date": first_snow_date,
        },
        "raw": payload,
    }
    try:
        container.create_item(body=doc)
    except Exception:
        # не валимо запит через логування
        pass

    return {"first_snow_date": first_snow_date}
