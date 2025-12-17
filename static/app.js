document.addEventListener("DOMContentLoaded", () => {

  const btnRefresh = document.getElementById("btnRefresh");
  const btnWhen = document.getElementById("btnWhen");
  const statusEl = document.getElementById("status");
  const forecastEl = document.getElementById("forecastText");
  const debugEl = document.getElementById("debug");
  const sunEl = document.getElementById("sun");

  /* ===== THEME ===== */
  function setTheme(theme) {
    document.body.classList.remove("sun", "snow", "snowsoon");
    document.body.classList.add(theme);
  }

  /* ===== SNOW ===== */
  function clearSnow() {
    document.querySelectorAll(".snowflake").forEach(e => e.remove());
  }

  function createSnow(count = 40) {
    clearSnow();
    for (let i = 0; i < count; i++) {
      const flake = document.createElement("div");
      flake.className = "snowflake";
      flake.textContent = "❄";
      flake.style.left = Math.random() * 100 + "vw";
      flake.style.fontSize = (Math.random() * 16 + 10) + "px";
      flake.style.animationDuration = (Math.random() * 5 + 5) + "s";
      flake.style.opacity = Math.random();
      document.body.appendChild(flake);
    }
  }

  /* ===== UTILS ===== */
  async function safeJson(response) {
    const text = await response.text();
    try {
      return { ok: true, data: JSON.parse(text), raw: text };
    } catch {
      return { ok: false, raw: text };
    }
  }

  /* ===== REFRESH ===== */
  btnRefresh.addEventListener("click", async () => {
    statusEl.textContent = "Оновлюю…";
    btnRefresh.disabled = true;
    btnWhen.disabled = true;

    try {
      const res = await fetch("/refresh", { method: "POST" });
      const parsed = await safeJson(res);

      if (!res.ok || !parsed.ok) {
        statusEl.textContent = "Помилка";
        debugEl.classList.remove("hidden");
        debugEl.textContent = parsed.raw;
        return;
      }

      const data = parsed.data;

      if (data.is_snowing) {
        setTheme("snow");
        sunEl.style.display = "none";
        createSnow(60);
        statusEl.textContent = "Пора.";
        debugEl.classList.remove("hidden");
        debugEl.textContent = JSON.stringify(data, null, 2);
        btnWhen.classList.add("hidden");
      } else {
        setTheme("sun");
        sunEl.style.display = "block";
        clearSnow();
        statusEl.textContent = "Ще рано";
        debugEl.classList.add("hidden");
        btnWhen.classList.remove("hidden");
      }

    } catch (e) {
      statusEl.textContent = "Помилка";
      debugEl.classList.remove("hidden");
      debugEl.textContent = String(e);
    } finally {
      btnRefresh.disabled = false;
      btnWhen.disabled = false;
    }
  });

  /* ===== FORECAST ===== */
  btnWhen.addEventListener("click", async () => {
    forecastEl.classList.remove("hidden");
    forecastEl.textContent = "Дивлюсь прогноз…";
    btnWhen.disabled = true;

    try {
      const res = await fetch("/forecast");
      const parsed = await safeJson(res);

      if (!res.ok || !parsed.ok) {
        forecastEl.textContent = "Невідомо";
        return;
      }

      const d = parsed.data.first_snow_date;

      if (d) {
        forecastEl.textContent = "Сніг очікується: " + d;
        setTheme("snowsoon");
        sunEl.style.display = "none";
        createSnow(25);
      } else {
        forecastEl.textContent = "Невідомо";
      }

    } catch {
      forecastEl.textContent = "Невідомо";
    } finally {
      btnWhen.disabled = false;
    }
  });

});
