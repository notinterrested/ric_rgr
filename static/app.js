// static/app.js

// Елементи зі сторінки
const btnRefresh = document.getElementById("btnRefresh");
const btnWhen = document.getElementById("btnWhen");
const statusEl = document.getElementById("status");
const forecastEl = document.getElementById("forecastText");
const debugEl = document.getElementById("debug");
const sunEl = document.getElementById("sun");

// --- Snow helpers ---
function createSnow() {
  // не множимо сніжинки безконтрольно
  clearSnow();

  for (let i = 0; i < 40; i++) {
    const flake = document.createElement("div");
    flake.className = "snowflake";
    flake.textContent = "❄";
    flake.style.left = (Math.random() * 100) + "vw";
    flake.style.fontSize = (Math.random() * 16 + 10) + "px";
    flake.style.animationDuration = (Math.random() * 5 + 5) + "s";
    flake.style.opacity = Math.random();
    document.body.appendChild(flake);
  }
}

function clearSnow() {
  document.querySelectorAll(".snowflake").forEach(e => e.remove());
}

// --- UI helpers ---
function showDebug(text) {
  debugEl.classList.remove("hidden");
  debugEl.textContent = text;
}

function hideDebug() {
  debugEl.classList.add("hidden");
  debugEl.textContent = "";
}

function showNoSnowUI() {
  hideDebug();                       // коли нема снігу — debug ховаємо
  btnWhen.classList.remove("hidden"); // показуємо "а коли буде?"
  forecastEl.classList.add("hidden");
  forecastEl.textContent = "";
}

function showSnowUI(data) {
  btnWhen.classList.add("hidden");
  forecastEl.classList.add("hidden");
  forecastEl.textContent = "";
  showDebug(JSON.stringify(data, null, 2));
}

// читаємо response як текст і пробуємо парсити JSON
async function safeJsonFromResponse(response) {
  const text = await response.text();
  try {
    return { ok: true, data: JSON.parse(text), raw: text };
  } catch {
    return { ok: false, data: null, raw: text };
  }
}

// --- Main actions ---
async function refreshWeather() {
  statusEl.textContent = "Оновлюю…";
  btnRefresh.disabled = true;
  btnWhen.disabled = true;

  try {
    const res = await fetch("/refresh", { method: "POST" });
    const parsed = await safeJsonFromResponse(res);

    if (!res.ok || !parsed.ok) {
      statusEl.textContent = "Помилка";
      showDebug("HTTP " + res.status + "\n\n" + parsed.raw);
      btnWhen.classList.add("hidden");
      return;
    }

    const data = parsed.data;

    if (data.is_snowing) {
      document.body.className = "snow";
      sunEl.style.display = "none";
      createSnow();
      statusEl.textContent = "Пора.";
      showSnowUI(data);
    } else {
      document.body.className = "sun";
      sunEl.style.display = "block";
      clearSnow();
      statusEl.textContent = "Ще рано";
      showNoSnowUI();
    }
  } catch (e) {
    statusEl.textContent = "Помилка запиту";
    showDebug(String(e));
    btnWhen.classList.add("hidden");
  } finally {
    btnRefresh.disabled = false;
    btnWhen.disabled = false;
  }
}

async function getForecast() {
  forecastEl.classList.remove("hidden");
  forecastEl.textContent = "Дивлюсь прогноз…";
  btnWhen.disabled = true;

  try {
    const res = await fetch("/forecast");
    const parsed = await safeJsonFromResponse(res);

    if (!res.ok || !parsed.ok) {
      forecastEl.textContent = "Не вдалось отримати прогноз";
      showDebug("HTTP " + res.status + "\n\n" + parsed.raw);
      return;
    }

    const d = parsed.data.first_snow_date;
    forecastEl.textContent = d ? ("Сніг очікується: " + d) : "невідомо";
  } catch (e) {
    forecastEl.textContent = "Помилка запиту прогнозу";
    showDebug(String(e));
  } finally {
    btnWhen.disabled = false;
  }
}

// --- Events ---
btnRefresh.addEventListener("click", refreshWeather);
btnWhen.addEventListener("click", getForecast);

// стартовий стан (не обов'язково)
statusEl.textContent = "Натисни “Оновити”";
