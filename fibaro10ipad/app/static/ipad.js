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

const numberFormatter = new Intl.NumberFormat("nb-NO", { maximumFractionDigits: 0 });

function formatMoney(value) {
  return `${numberFormatter.format(Number(value || 0))} kr`;
}

function formatCount(value) {
  return numberFormatter.format(Number(value || 0));
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function safeText(value, fallback = "-") {
  if (value === null || value === undefined || value === "") return fallback;
  return String(value);
}

function setText(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}

function setClass(id, classes) {
  const el = document.getElementById(id);
  if (el) el.className = classes;
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

function deltaMoney(current, reference) {
  const currentNumber = Number(current || 0);
  const referenceNumber = Number(reference || 0);
  const delta = currentNumber - referenceNumber;
  const pct = referenceNumber ? Math.round((delta / referenceNumber) * 100) : null;
  return {
    value: `${delta > 0 ? "+" : ""}${formatMoney(delta)}`,
    percent: pct === null ? "" : `${pct > 0 ? "+" : ""}${pct}%`,
    raw: delta,
    current: currentNumber,
    reference: referenceNumber,
    className: deltaClass(delta),
  };
}

function clamp(value, min = 0, max = 100) {
  return Math.min(max, Math.max(min, Number(value || 0)));
}

function percent(part, total) {
  const denominator = Number(total || 0);
  if (!denominator) return 0;
  return clamp((Number(part || 0) / denominator) * 100);
}

function progressPercent(current, reference) {
  const denominator = Number(reference || 0);
  if (!denominator) return 0;
  return clamp((Number(current || 0) / denominator) * 100, 0, 130);
}

function wholePercent(value) {
  return `${Math.round(Number(value || 0))}%`;
}

function deltaIcon(diff) {
  if (Number(diff?.raw || 0) > 0) return "↑";
  if (Number(diff?.raw || 0) < 0) return "↓";
  return "→";
}

function referenceLabel(period) {
  if (period?.key === "today") return "Mot i går";
  if (period?.key === "week") return "Mot forrige uke";
  if (period?.key === "month") return "Mot forrige måned";
  return `Mot ${new Date().getFullYear() - 1}`;
}

function yearFromLabel(label) {
  const match = String(label || "").match(/\b20\d{2}\b/);
  return match ? match[0] : "";
}

function extraReferenceLabel(period, extra) {
  if (period?.key === "today") return "Mot forrige uke";
  const label = safeText(extra?.label, "Ekstra");
  const year = yearFromLabel(label);
  if (period?.key === "week" && year) return `Samme uke ${year}`;
  if (period?.key === "month" && year) return `Samme måned ${year}`;
  if (period?.key === "year" && year) return `Mot ${year}`;
  return label
    .replace("Sammenlignet med tilsvarende datatidspunkt i ", "Mot ")
    .replace("Sammenlignet med tilsvarende datatidspunkt ", "Mot ");
}

function driverMark(kind) {
  if (kind === "sun") {
    return `<span class="driver-mark sun"><img src="/static/lilletorget-mark.png" alt=""></span>`;
  }
  return `<span class="driver-mark parking">P</span>`;
}

function driverRow(kind, label, amount, count, reference, extraReference) {
  const diff = deltaMoney(amount, reference);
  const extra = deltaMoney(amount, extraReference);
  const avg = Number(count || 0) ? `${formatMoney(Number(amount || 0) / Number(count))} snitt` : "Ingen snitt";
  return `
    <tr>
      <td>
        <span class="driver-name">
          ${driverMark(kind)}
          <span>
            <span class="driver-label">${escapeHtml(label)}</span>
            <span class="driver-meta">${formatCount(count)} stk · ${escapeHtml(avg)}</span>
          </span>
        </span>
      </td>
      <td class="driver-value">${formatMoney(amount)}</td>
      <td><span class="delta ${diff.className}">${escapeHtml(diff.value)}<small>${escapeHtml(diff.percent)}</small></span></td>
      <td><span class="delta ${extra.className}">${escapeHtml(extra.value)}<small>${escapeHtml(extra.percent)}</small></span></td>
    </tr>`;
}

function renderPeriodCard(period) {
  const extra = firstExtra(period);
  const sunShare = percent(period.sol, period.total);
  const parkingShare = percent(period.parking, period.total);
  const reference = deltaMoney(period.total, period.previousTotal);
  const extraReference = deltaMoney(period.total, extra?.total);
  const referenceProgress = progressPercent(period.total, period.previousFullTotal || period.previousTotal);
  const extraProgress = progressPercent(period.total, extra?.fullTotal || extra?.total);
  const fullPieces = [];
  if (period.previousFullLabel && period.previousFullTotal !== undefined) {
    fullPieces.push({
      label: period.previousFullLabel,
      total: period.previousFullTotal,
      remaining: Number(period.previousFullTotal || 0) - Number(period.total || 0),
      progress: referenceProgress,
    });
  }
  if (extra?.fullLabel && extra.fullTotal !== undefined) {
    fullPieces.push({
      label: extra.fullLabel,
      total: extra.fullTotal,
      remaining: Number(extra.fullTotal || 0) - Number(period.total || 0),
      progress: extraProgress,
    });
  }
  return `
    <article class="period-card period-card-${escapeHtml(safeText(period.key, "period"))}" style="--sun-share:${sunShare}%; --parking-share:${parkingShare}%">
      <div class="period-top">
        <div>
          <h2 class="period-title">${escapeHtml(safeText(period.title))}</h2>
          <p class="period-subtitle">${escapeHtml(periodMeta(period))}</p>
        </div>
        <p class="period-total">${formatMoney(period.total)}</p>
      </div>
      <div class="period-split">
        <div class="split-meter" aria-hidden="true"></div>
        <div class="split-legend">
          <span><i class="sun-dot"></i>Soling ${wholePercent(sunShare)}</span>
          <span><i class="parking-dot"></i>Parkering ${wholePercent(parkingShare)}</span>
        </div>
      </div>
      <div class="period-delta-row">
        <div class="period-delta-card ${reference.className}">
          <span>${escapeHtml(referenceLabel(period))}</span>
          <strong>${escapeHtml(reference.value)}</strong>
          <small>${escapeHtml(reference.percent)}</small>
        </div>
        <div class="period-delta-card ${extraReference.className}">
          <span>${escapeHtml(extraReferenceLabel(period, extra))}</span>
          <strong>${escapeHtml(extraReference.value)}</strong>
          <small>${escapeHtml(extraReference.percent)}</small>
        </div>
      </div>
      <table class="driver-table">
        <thead>
          <tr>
            <th>Linje</th>
            <th>Hittil</th>
            <th>${escapeHtml(referenceLabel(period))}</th>
            <th>${escapeHtml(extraReferenceLabel(period, extra))}</th>
          </tr>
        </thead>
        <tbody>
          ${driverRow("sun", "Soling", period.sol, period.solCount, period.previousSol, extra?.sol)}
          ${driverRow("parking", "Parkering", period.parking, period.parkingCount, period.previousParking, extra?.parking)}
        </tbody>
      </table>
      <div class="period-foot">${fullPieces.length ? fullPieces.map((part) => `
        <span style="--progress:${part.progress}%">
          <small>${escapeHtml(part.label)}</small>
          <strong>${formatMoney(part.total)}</strong>
          <em>Gjenstår ${formatMoney(part.remaining)}</em>
          <i></i>
        </span>`).join("") : "<span>Ingen hel referanseperiode</span>"}</div>
    </article>`;
}

function datasourceCounts(services) {
  const counts = { total: services.length, ok: 0, warn: 0, bad: 0, unknown: 0 };
  for (const service of services) {
    const key = ["ok", "warn", "bad"].includes(service?.status) ? service.status : "unknown";
    counts[key] += 1;
  }
  return counts;
}

function latestItem(labelNeedle) {
  return (state.data?.overview?.latestItems || []).find((item) =>
    String(item.label || "").toLowerCase().includes(labelNeedle),
  );
}

function renderHero(periods) {
  const hero = document.getElementById("heroGrid");
  if (!hero) return;
  const today = periods.find((period) => period.key === "today") || periods[0];
  if (!today) {
    hero.innerHTML = `<div class="empty">Ingen hovedtall tilgjengelig.</div>`;
    return;
  }
  const extra = firstExtra(today);
  const diffYesterday = deltaMoney(today.total, today.previousTotal);
  const diffWeek = deltaMoney(today.total, extra?.total);
  const sunShare = percent(today.sol, today.total);
  const parkingShare = percent(today.parking, today.total);
  const previousProgress = progressPercent(today.total, today.previousFullTotal || today.previousTotal);
  const weekProgress = progressPercent(today.total, extra?.fullTotal || extra?.total);
  const latestSun = latestItem("soling");
  const latestParking = latestItem("parkering");
  const services = state.data?.overview?.services || [];
  const counts = datasourceCounts(services);
  hero.innerHTML = `
    <article class="hero-card" style="--sun-share:${sunShare}%; --parking-share:${parkingShare}%; --prev-progress:${previousProgress}%; --week-progress:${weekProgress}%">
      <div class="hero-top">
        <div>
          <p class="eyebrow">Omsetning</p>
          <h2 class="hero-title">Hittil i dag</h2>
          <p class="hero-subtitle">${escapeHtml(periodMeta(today))}</p>
        </div>
        <div class="hero-number-stack">
          <span>Total nå</span>
          <p class="hero-total">${formatMoney(today.total)}</p>
        </div>
      </div>
      <div class="hero-split-meter" aria-hidden="true"></div>
      <div class="hero-drivers">
        <div class="driver-tile">
          <span>${driverMark("sun")} Soling</span>
          <strong>${formatMoney(today.sol)}</strong>
          <small>${formatCount(today.solCount)} stk · ${wholePercent(sunShare)}</small>
        </div>
        <div class="driver-tile">
          <span>${driverMark("parking")} Parkering</span>
          <strong>${formatMoney(today.parking)}</strong>
          <small>${formatCount(today.parkingCount)} stk · ${wholePercent(parkingShare)}</small>
        </div>
      </div>
      <div class="hero-reference">
        <div class="reference-chip ${diffYesterday.className}">
          <div>
            <span>Mot i går samme tidspunkt</span>
            <strong>${escapeHtml(diffYesterday.value)}</strong>
            <small>${escapeHtml(diffYesterday.percent)}</small>
          </div>
          <em>${deltaIcon(diffYesterday)}</em>
        </div>
        <div class="reference-chip ${diffWeek.className}">
          <div>
            <span>Mot samme ukedag forrige uke</span>
            <strong>${escapeHtml(diffWeek.value)}</strong>
            <small>${escapeHtml(diffWeek.percent)}</small>
          </div>
          <em>${deltaIcon(diffWeek)}</em>
        </div>
      </div>
      <div class="hero-progress-row">
        <span><small>Mot hel gårsdag</small><strong>${wholePercent(previousProgress)}</strong><i></i></span>
        <span><small>Mot hel forrige uke-dag</small><strong>${wholePercent(weekProgress)}</strong><i></i></span>
      </div>
    </article>
    <aside class="hero-side">
      <div class="side-card">
        <h3>Datakilder</h3>
        <strong>${counts.ok}/${counts.total} OK</strong>
        <small>${counts.warn} treg, ${counts.bad} feil, ${counts.unknown} ukjent</small>
      </div>
      <div class="side-card">
        <h3>Siste soling</h3>
        <strong>${escapeHtml(safeText(latestSun?.value))}</strong>
        <small>${escapeHtml(safeText(latestSun?.detail, ""))}</small>
      </div>
      <div class="side-card">
        <h3>Siste parkering</h3>
        <strong>${escapeHtml(safeText(latestParking?.value))}</strong>
        <small>${escapeHtml(safeText(latestParking?.detail, ""))}</small>
      </div>
    </aside>`;
}

function renderOverview() {
  const periods = state.data?.overview?.statusPeriods || [];
  renderHero(periods);
  const grid = document.getElementById("periodGrid");
  if (!grid) return;
  const detailPeriods = periods.filter((period) => period?.key !== "today");
  grid.classList.toggle("period-grid-trio", detailPeriods.length === 3);
  grid.innerHTML = detailPeriods.length
    ? detailPeriods.map(renderPeriodCard).join("")
    : `<div class="empty">Ingen omsetningsperioder tilgjengelig.</div>`;
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
    ? cards.slice(0, 8).map((card) => `
        <div class="mini-card">
          <span>${escapeHtml(safeText(card.title))}</span>
          <strong>${escapeHtml(safeText(card.value))}${card.unit ? ` ${escapeHtml(card.unit)}` : ""}</strong>
          <small>${escapeHtml(safeText(card.detail, ""))}</small>
        </div>`).join("")
    : `<div class="empty">Ingen nøkkeltall tilgjengelig.</div>`;
}

function renderEvents(id, items) {
  const el = document.getElementById(id);
  if (!el) return;
  el.innerHTML = items.length
    ? items.slice(0, 10).map((item) => `
        <div class="event-row">
          <div>
            <strong>${escapeHtml(safeText(item.label))}</strong>
            <small>${escapeHtml(safeText(item.detail, ""))}</small>
          </div>
          <strong>${escapeHtml(safeText(item.value))}</strong>
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
    op.innerHTML = `<strong>${escapeHtml(safeText(operating.label))}</strong><span>${escapeHtml(safeText(operating.detail, ""))}</span>`;
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
        return `<span class="state-pill ${cls}">${escapeHtml(safeText(item.label))}</span>`;
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
    ? sorted.slice(0, 14).map((service) => `
        <div class="service-row">
          <div>
            <strong>#${escapeHtml(safeText(service.sourceNo, "-"))} ${escapeHtml(safeText(service.label))}</strong>
            <small>${escapeHtml(safeText(service.detail, ""))}</small>
          </div>
          <span class="service-status ${escapeHtml(safeText(service.status, "unknown"))}">${escapeHtml(safeText(service.status, "?"))}</span>
        </div>`).join("")
    : `<div class="empty">Ingen datakilder tilgjengelig.</div>`;
}

function updateTopStatus() {
  const overview = state.data?.overview || {};
  const operating = overview.operatingWindow || {};
  const services = overview.services || [];
  const counts = datasourceCounts(services);
  const datasourceTone = counts.bad > 0 ? "bad" : counts.warn > 0 || counts.unknown > 0 ? "warn" : "ok";
  setText("topOperatingStatus", `${safeText(operating.label, "Ukjent")} · ${safeText(operating.detail, "")}`);
  setText("topDatasourceStatus", `Datakilder ${counts.ok}/${counts.total}`);
  setClass("topOperatingStatus", `top-pill ${operating.open ? "ok" : "warn"}`);
  setClass("topDatasourceStatus", `top-pill ${datasourceTone}`);
}

function renderAll() {
  const overview = state.data?.overview;
  setText("userButton", (state.data?.user?.username || "?").slice(0, 1).toUpperCase());
  setText("buildBadge", state.data?.app?.build || "1472");
  setText("syncStatus", overview?.generatedAt ? `Sist oppdatert ${new Date(overview.generatedAt).toLocaleString("nb-NO")}` : "Ingen data");
  updateTopStatus();
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
