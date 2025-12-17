import os
import uuid
from datetime import datetime, timezone

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from azure.cosmos import CosmosClient, exceptions

app = FastAPI()

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
    return """
<!doctype html>
<html>
  <head>
    <meta charset="utf-8"/>
    <title>Bukovel Snow Checker</title>
  </head>
  <body style="font-family: Arial, sans-serif; padding: 24px;">
    <h2>Bukovel: чи падає сніг?</h2>

    <button id="btn">Оновити</button>
    <p id="status" style="margin-top: 16px; font-size: 18px;">Натисни "Оновити"</p>
    <pre id="details" style="background:#f4f4f4; padding:12px;"></pre>

    <script>
      const btn = document.getElementById("btn");
      const statusEl = document.getElementById("status");
      const detailsEl = document.getElementById("details");

      btn.addEventListener("click", async () => {
        statusEl.textContent = "Оновлюю...";
        detailsEl.textContent = "";

        try {
          const res = await fetch("/refresh", { method: "POST" });
          const data = await res.json();

          if (!res.ok) {
            statusEl.textContent = "Помилка";
            detailsEl.textContent = JSON.stringify(data, null, 2);
            return;
          }

          statusEl.textContent = data.is_snowing ? "падає сніг" : "снігу немає";
          detailsEl.textContent = JSON.stringify(data, null, 2);
        } catch (e) {
          statusEl.textContent = "Помилка запиту";
          detailsEl.textContent = String(e);
        }
      });
    </script>
  </body>
</html>
"""


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
