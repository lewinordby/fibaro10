const state = {
  data: null,
  activeView: "overview",
};

const viewTitles = {
  overview: "Oversikt",
  parking: "Parkering",
  sun: "Soling",
  ops: "Drift",
};

function formatMoney(value) {
  const number = Number(value || 0);
  return `${new Intl.NumberFormat("nb-NO", { maximumFractionDigits: 0 }).format(number)} kr`;
}

function formatCount(value) {
  return new Intl.NumberFormat("nb-NO", { maximumFractionDigits: 0 }).format(Number(value || 0));
}

function safeText(value, fallback = "-") {
  if (value === null || value === undefined || value === "") return fallback;
  return String(value);
}

function setText(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}

function periodMeta(period) {
  const parts = [];
  if (period?.solAsOfLabel) parts.push(`Sol ${period.solAsOfLabel}`);
  if (period?.parkingAsOfLabel) parts.push(`Parkering ${period.parkingAsOfLabel}`);
  return parts.join(" · ");
}

function firstExtra(period) {
  return Array.isArray(period?.extraComparisons) && period.extraComparisons.length ? period.extraComparisons[0] : null;
}

function deltaClass(value) {
  const number = Number(value || 0);
  if (number > 0) return "positive";
  if (number < 0) return "negative";
  return "";
}

function deltaText(current, reference) {
  const delta = Number(current || 0) - Number(reference || 0);
  const pct = reference ? Math.round((delta / Number(reference)) * 100) : null;
  return {
    value: `${delta > 0 ? "+" : ""}${formatMoney(delta)}`,
    percent: pct === null ? "" : `${pct > 0 ? "+" : ""}${pct}%`,
    className: deltaClass(delta),
  };
}

function activityDeltaText(current, reference) {
  const delta = Number(current || 0) - Number(reference || 0);
  const pct = reference ? Math.round((delta / Number(reference)) * 100) : null;
  return {
    value: `${delta > 0 ? "+" : ""}${formatCount(delta)} stk`,
    percent: pct === null ? "" : `${pct > 0 ? "+" : ""}${pct}%`,
    className: deltaClass(delta),
  };
}

function driverRow(kind, label, amount, count, reference, extraReference) {
  const diff = deltaText(amount, reference);
  const extra = deltaText(amount, extraReference);
  const avg = count ? `${formatMoney(Number(amount || 0) / Number(count))} snitt` : "Ingen snitt";
  const mark =
    kind === "sun"
      ? `<span class="driver-mark sun"><img src="/static/lilletorget-mark.png" alt=""></span>`
      : `<span class="driver-mark parking">P</span>`;
  return `
    <tr>
      <td>
        <span class="driver-name">
          ${mark}
          <span>
            <span class="driver-label">${label}</span>
            <span class="driver-meta">${formatCount(count)} stk · ${avg}</span>
          </span>
        </span>
      </td>
      <td class="driver-value">${formatMoney(amount)}</td>
      <td><span class="delta ${diff.className}">${diff.value}<small>${diff.percent}</small></span></td>
      <td><span class="delta ${extra.className}">${extra.value}<small>${extra.percent}</small></span></td>
    </tr>`;
}

function renderPeriodCard(period) {
  const extra = firstExtra(period);
  const referenceLabel = period.key === "today"
    ? "Mot i går"
    : period.key === "week"
      ? "Mot forrige uke"
      : period.key === "month"
        ? "Mot forrige måned"
        : `Mot ${new Date().getFullYear() - 1}`;
  const extraLabel = period.key === "today"
    ? "Mot forrige uke"
    : extra?.label?.replace("Sammenlignet med tilsvarende datatidspunkt i ", "Mot ") || "Ekstra";
  const fullPieces = [];
  if (period.previousFullLabel && period.previousFullTotal !== undefined) {
    fullPieces.push(`${period.previousFullLabel}: ${formatMoney(period.previousFullTotal)}`);
    fullPieces.push(`gjenstår ${formatMoney(Number(period.previousFullTotal || 0) - Number(period.total || 0))}`);
  }
  if (extra?.fullLabel && extra.fullTotal !== undefined) {
    fullPieces.push(`${extra.fullLabel}: ${formatMoney(extra.fullTotal)}`);
    fullPieces.push(`gjenstår ${formatMoney(Number(extra.fullTotal || 0) - Number(period.total || 0))}`);
  }
  return `
    <article class="period-card">
      <div class="period-top">
        <div>
          <h2 class="period-title">${safeText(period.title)}</h2>
          <p class="period-subtitle">${periodMeta(period)}</p>
        </div>
        <p class="period-total">${formatMoney(period.total)}</p>
      </div>
      <table class="driver-table">
        <thead>
          <tr>
            <th>Linje</th>
            <th>Hittil</th>
            <th>${referenceLabel}</th>
            <th>${extraLabel}</th>
          </tr>
        </thead>
        <tbody>
          ${driverRow("sun", "Soling", period.sol, period.solCount, period.previousSol, extra?.sol)}
          ${driverRow("parking", "Parkering", period.parking, period.parkingCount, period.previousParking, extra?.parking)}
        </tbody>
      </table>
      <div class="period-foot">${fullPieces.map((part) => `<span>${part}</span>`).join("") || "<span>Ingen hel referanseperiode</span>"}</div>
    </article>`;
}

function renderOverview() {
  const periods = state.data?.overview?.statusPeriods || [];
  const grid = document.getElementById("periodGrid");
  if (!grid) return;
  grid.innerHTML = periods.length ? periods.map(renderPeriodCard).join("") : `<div class="empty">Ingen omsetningsperioder tilgjengelig.</div>`;
}

function overviewCardsByGroup(group) {
  return (state.data?.overview?.cards || []).filter((card) => String(card.group || "").toLowerCase() === group);
}

function latestByLabel(needle) {
  return (state.data?.overview?.latestItems || []).filter((item) => String(item.label || "").toLowerCase().includes(needle));
}

function renderMiniCards(id, cards) {
  const el = document.getElementById(id);
  if (!el) return;
  el.innerHTML = cards.length
    ? cards.slice(0, 6).map((card) => `
        <div class="mini-card">
          <span>${safeText(card.title)}</span>
          <strong>${safeText(card.value)}${card.unit ? ` ${card.unit}` : ""}</strong>
          <small>${safeText(card.detail, "")}</small>
        </div>`).join("")
    : `<div class="empty">Ingen nøkkeltall tilgjengelig.</div>`;
}

function renderEvents(id, items) {
  const el = document.getElementById(id);
  if (!el) return;
  el.innerHTML = items.length
    ? items.slice(0, 8).map((item) => `
        <div class="event-row">
          <div>
            <strong>${safeText(item.label)}</strong>
            <small>${safeText(item.detail, "")}</small>
          </div>
          <strong>${safeText(item.value)}</strong>
        </div>`).join("")
    : `<div class="empty">Ingen siste hendelser tilgjengelig.</div>`;
}

function renderParking() {
  renderMiniCards("parkingCards", overviewCardsByGroup("parkering"));
  renderEvents("parkingList", latestByLabel("parkering"));
}

function renderSun() {
  renderMiniCards("sunCards", overviewCardsByGroup("soling"));
  renderEvents("sunList", latestByLabel("soling"));
}

function renderOps() {
  const overview = state.data?.overview || {};
  const operating = overview.operatingWindow || {};
  const op = document.getElementById("operatingStatus");
  if (op) {
    op.innerHTML = `<strong>${safeText(operating.label)}</strong><span>${safeText(operating.detail, "")}</span>`;
  }
  renderStateStrip("lightStrip", overview.lightItems || []);
  renderStateStrip("fanStrip", overview.fanItems || []);
  renderServices(overview.services || []);
}

function renderStateStrip(id, items) {
  const el = document.getElementById(id);
  if (!el) return;
  el.innerHTML = items.length
    ? items.map((item) => {
        const cls = item.state === true ? "on" : item.state === null ? "unknown" : "";
        return `<span class="state-pill ${cls}">${safeText(item.label)}</span>`;
      }).join("")
    : `<div class="empty">Ingen status tilgjengelig.</div>`;
}

function renderServices(services) {
  const el = document.getElementById("serviceList");
  if (!el) return;
  const sorted = [...services].sort((a, b) => {
    const weight = { bad: 0, warn: 1, unknown: 2, ok: 3 };
    return (weight[a.status] ?? 2) - (weight[b.status] ?? 2);
  });
  el.innerHTML = sorted.length
    ? sorted.slice(0, 12).map((service) => `
        <div class="service-row">
          <div>
            <strong>#${safeText(service.sourceNo, "-")} ${safeText(service.label)}</strong>
            <small>${safeText(service.detail, "")}</small>
          </div>
          <span class="service-status ${safeText(service.status, "unknown")}">${safeText(service.status, "?")}</span>
        </div>`).join("")
    : `<div class="empty">Ingen datakilder tilgjengelig.</div>`;
}

function renderAll() {
  const overview = state.data?.overview;
  setText("userButton", (state.data?.user?.username || "?").slice(0, 1).toUpperCase());
  setText("syncStatus", overview?.generatedAt ? `Sist oppdatert ${new Date(overview.generatedAt).toLocaleString("nb-NO")}` : "Ingen data");
  renderOverview();
  renderParking();
  renderSun();
  renderOps();
}

function showView(view) {
  state.activeView = view;
  document.querySelectorAll(".mode-tabs button").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.view === view);
  });
  document.querySelectorAll(".view").forEach((section) => section.classList.remove("is-active"));
  document.getElementById(`${view}View`)?.classList.add("is-active");
  setText("mainTitle", viewTitles[view] || "Oversikt");
}

async function loadBootstrap() {
  setText("syncStatus", "Henter data");
  const response = await fetch("/api/bootstrap", { credentials: "same-origin", headers: { Accept: "application/json" } });
  if (response.status === 401) {
    window.location.href = "/auth/login";
    return;
  }
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(payload?.detail || `${response.status} ${response.statusText}`);
  }
  state.data = payload;
  renderAll();
}

function boot() {
  document.querySelectorAll(".mode-tabs button").forEach((button) => {
    button.addEventListener("click", () => showView(button.dataset.view || "overview"));
  });
  document.getElementById("refreshButton")?.addEventListener("click", async () => {
    try {
      await loadBootstrap();
    } catch (error) {
      setText("syncStatus", `Feil: ${error.message}`);
    }
  });
  loadBootstrap().catch((error) => setText("syncStatus", `Feil: ${error.message}`));
  window.setInterval(() => {
    loadBootstrap().catch((error) => setText("syncStatus", `Feil: ${error.message}`));
  }, 60_000);
}

document.addEventListener("DOMContentLoaded", boot);
