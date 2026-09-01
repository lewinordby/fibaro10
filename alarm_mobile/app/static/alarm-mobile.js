const state = {
  data: null,
  currentView: "overview",
  currentMonitorId: "",
  busy: false,
};

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

function text(value, fallback = "") {
  if (value === null || value === undefined) return fallback;
  const result = String(value).trim();
  return result || fallback;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function number(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function formatStamp(value, seconds = false) {
  if (!value) return "Ikke registrert";
  const parsed = new Date(String(value).replace(" ", "T"));
  if (Number.isNaN(parsed.getTime())) return String(value);
  return new Intl.DateTimeFormat("no-NO", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: seconds ? "2-digit" : undefined,
  }).format(parsed);
}

function formatAge(value) {
  if (!value) return "ukjent";
  const parsed = new Date(String(value).replace(" ", "T"));
  if (Number.isNaN(parsed.getTime())) return "ukjent";
  const seconds = Math.max(0, Math.round((Date.now() - parsed.getTime()) / 1000));
  if (seconds < 60) return `${seconds} sek siden`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)} min siden`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)} t siden`;
  return `${Math.floor(seconds / 86400)} d siden`;
}

function severityClass(value) {
  const normalized = text(value).toLowerCase();
  if (["alert", "error", "active", "changed", "anomaly"].includes(normalized)) return "is-alert";
  if (["warning", "waiting", "acknowledged", "obscured"].includes(normalized)) return "is-warning";
  if (["normal", "free", "ok", "resolved", "active-session"].includes(normalized)) return "is-ok";
  return "is-neutral";
}

function severityLabel(value) {
  return {
    alert: "Alarm",
    warning: "Følg med",
    waiting: "Venter",
    active: "Aktiv",
    acknowledged: "Sett",
    resolved: "Løst",
    normal: "Normal",
    free: "Ledig",
    changed: "Endring",
    obscured: "Tildekket",
    uncalibrated: "Mangler referanse",
    error: "Feil",
    disabled: "Stengt",
  }[text(value).toLowerCase()] || text(value, "Ukjent");
}

function roomIsDisabled(room) {
  return room?.bedEnabled === false || text(room?.severity).toLowerCase() === "disabled";
}

function roomDisplaySeverity(room) {
  return roomIsDisabled(room) ? "disabled" : room?.severity;
}

function roomDisplayLabel(room) {
  if (roomIsDisabled(room)) return "Stengt";
  return room?.doorStateLabel || (room?.isOccupied ? "Lukket" : "Åpen");
}

function subscription(key) {
  return (state.data?.notifications?.subscriptions || []).find((item) => item?.key === key) || {};
}

function setMessage(message, error = false) {
  const element = $("#appMessage");
  if (!element) return;
  element.textContent = message || "";
  element.classList.toggle("is-error", error);
}

function routeFromUrl() {
  const params = new URLSearchParams(window.location.search);
  if (params.has("alarm")) return "doors";
  if (params.has("monitor")) return "bollardDetail";
  if (params.has("incident")) return "bollards";
  const section = params.get("section");
  return { dorer: "doors", pullerter: "bollards", konto: "account" }[section] || "overview";
}

function routeValue(view) {
  return { doors: "dorer", bollards: "pullerter", bollardDetail: "pullerter", account: "konto" }[view] || "status";
}

function showView(view, { updateUrl = true } = {}) {
  state.currentView = view;
  for (const name of ["overview", "doors", "bollards", "bollardDetail", "account"]) {
    $(`#${name}View`)?.classList.toggle("is-hidden", name !== view);
  }
  const navView = view === "bollardDetail" ? "bollards" : view;
  $$('[data-view]').forEach((button) => button.classList.toggle("is-active", button.dataset.view === navView));
  if (updateUrl) {
    const url = new URL(window.location.href);
    url.searchParams.set("section", routeValue(view));
    if (view !== "doors") url.searchParams.delete("alarm");
    if (view !== "bollards") url.searchParams.delete("incident");
    if (view !== "bollardDetail") url.searchParams.delete("monitor");
    window.history.pushState({}, "", `${url.pathname}${url.search}`);
  }
  window.scrollTo({ top: 0, behavior: "auto" });
}

function monitorIdFromUrl() {
  return new URLSearchParams(window.location.search).get("monitor") || "";
}

function statusIcon(kind) {
  if (kind === "alert") {
    return '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 9v4M12 17h.01M10.3 3.7 2.2 18a2 2 0 0 0 1.8 3h16a2 2 0 0 0 1.8-3L13.7 3.7a2 2 0 0 0-3.4 0Z"/></svg>';
  }
  if (kind === "door") {
    return '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M13 4h6v16h-6M13 4 5 2v20l8-2zM9 12h.01"/></svg>';
  }
  return '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 3h12M8 3v18h8V3M5 21h14M8 8h8"/></svg>';
}

function renderOverview() {
  const root = $("#overviewView");
  if (!root) return;
  const doors = state.data?.doors || {};
  const bollards = state.data?.bollards || {};
  const doorSummary = doors.summary || {};
  const bollardSummary = bollards.summary || {};
  const activeDoorAlarms = doors.alarms || [];
  const activeIncidents = (bollards.incidents || []).filter((item) => ["active", "acknowledged"].includes(text(item.status).toLowerCase()));
  const total = activeDoorAlarms.length + activeIncidents.length;
  const errors = Object.values(state.data?.errors || {});
  const overall = errors.length ? "Datakildefeil" : total ? `${total} aktive varsler` : "Alt er normalt";
  const overallClass = errors.length || total ? "is-alert" : "is-ok";

  const activeRows = [
    ...activeDoorAlarms.map((item) => ({
      type: "Dør",
      title: item.title || item.roomLabel || "Solrom",
      detail: item.detail || item.alarmReason || "Døralarm",
      target: `doors:${item.deviceKey || item.roomId || ""}`,
    })),
    ...activeIncidents.map((item) => ({
      type: "Pullert",
      title: item.display_name || item.bollard_key || "Kameravarsel",
      detail: `Registrert ${formatStamp(item.detected_at)}`,
      target: `bollards:${item.incident_id || ""}`,
    })),
  ];

  root.innerHTML = `
    <section class="appkit-page-title alarm-page-title">
      <div><p>Sikkerhet og kontroll</p><h1>Alarm</h1></div>
      <span>Oppdatert<br>${escapeHtml(formatAge(state.data?.generatedAt))}</span>
    </section>

    <section class="status-hero appkit-glance ${overallClass}">
      <div class="alarm-glance-head">
        <span class="status-hero-icon">${statusIcon(total || errors.length ? "alert" : "door")}</span>
        <div><span class="appkit-glance-kicker">Status akkurat nå</span><h2>${escapeHtml(overall)}</h2></div>
      </div>
      <div class="appkit-glance-metrics" style="--appkit-metric-count:3">
        <div><strong>${total}</strong><small>Aktive varsler</small></div>
        <div><strong>${number(doorSummary.rooms)}</strong><small>Solrom</small></div>
        <div><strong>${number(bollardSummary.inspection_objects)}</strong><small>Kontrollfelt</small></div>
      </div>
    </section>

    <div class="appkit-content-title"><h2>Områder</h2><span>Trykk for detaljer</span></div>
    <section class="summary-grid">
      <button type="button" class="summary-card" data-open-view="doors">
        <span class="summary-icon is-door">${statusIcon("door")}</span>
        <span><small>Dører og solrom</small><strong>${number(doorSummary.alarm)} alarm · ${number(doorSummary.watch)} følges</strong></span>
        <b>${number(doorSummary.rooms)}</b>
      </button>
      <button type="button" class="summary-card" data-open-view="bollards">
        <span class="summary-icon is-bollard">${statusIcon("bollard")}</span>
        <span><small>Pullerter og trapp</small><strong>${number(bollardSummary.active_incidents)} aktive avvik</strong></span>
        <b>${number(bollardSummary.inspection_objects)}</b>
      </button>
    </section>

    <section class="section-block active-section">
      <div class="section-title"><h2>Aktivt nå</h2><span>${activeRows.length}</span></div>
      <div class="event-list">
        ${activeRows.length ? activeRows.map((item) => `
          <button class="event-row" type="button" data-target="${escapeHtml(item.target)}">
            <span class="event-marker is-alert"></span>
            <span><small>${escapeHtml(item.type)}</small><strong>${escapeHtml(item.title)}</strong><em>${escapeHtml(item.detail)}</em></span>
            <b aria-hidden="true">›</b>
          </button>
        `).join("") : '<p class="empty-state">Ingen aktive alarmer eller kamerahendelser.</p>'}
      </div>
    </section>

    ${errors.length ? `<section class="source-error"><strong>Datakilder</strong>${errors.map((error) => `<p>${escapeHtml(error)}</p>`).join("")}</section>` : ""}
  `;

  $$('[data-open-view]', root).forEach((button) => button.addEventListener("click", () => showView(button.dataset.openView)));
  $$('[data-target]', root).forEach((button) => button.addEventListener("click", () => openTarget(button.dataset.target)));
}

function doorSessionSummary(room) {
  if (roomIsDisabled(room)) return `Sengen er slått av i Sun2 · dør ${text(room.doorStateLabel, "ukjent").toLowerCase()}`;
  const session = room.session || {};
  if (!room.isOccupied) return "Døren er åpen";
  if (!session || !Object.keys(session).length) return `Lukket ${room.occupiedDurationLabel || ""} · ingen soltime funnet`;
  const end = room.expectedExitLabel || session.endedLabel || session.endedAt;
  return `Soltime ${session.startedLabel || formatStamp(session.startedAt)} · forventet ut ${end || "-"}`;
}

function renderDoors() {
  const root = $("#doorsView");
  if (!root) return;
  const payload = state.data?.doors || {};
  const summary = payload.summary || {};
  const rooms = payload.rooms || [];
  const history = payload.history || [];
  const channel = subscription("doors");
  root.innerHTML = `
    <section class="view-head">
      <div><p class="eyebrow">Solrom</p><h1>Døralarmer</h1></div>
      <span class="count-badge ${number(summary.alarm) ? "is-alert" : "is-ok"}">${number(summary.alarm)} aktive</span>
    </section>

    <section class="metric-strip is-five">
      <div><small>Lukket</small><strong>${number(summary.active)}</strong></div>
      <div><small>Stengt</small><strong>${number(summary.disabled)}</strong></div>
      <div><small>Venter</small><strong>${number(summary.waiting)}</strong></div>
      <div><small>Følg med</small><strong>${number(summary.warning)}</strong></div>
      <div><small>Alarm</small><strong>${number(summary.alarm)}</strong></div>
    </section>

    <section class="channel-row">
      <span><strong>Dørvarsler i ntfy</strong><small>${channel.publishingEnabled ? "Varsling er aktiv" : "Kontroller abonnementet"}</small></span>
      ${channel.subscribeUrl ? `<a href="${escapeHtml(channel.subscribeUrl)}">Abonner</a>` : '<em>Ikke konfigurert</em>'}
    </section>

    <section class="section-block room-section">
      <div class="section-title"><h2>Romstatus</h2><span>${rooms.length}</span></div>
      <div class="room-grid">
        ${rooms.map((room) => `
          <article class="room-card ${severityClass(roomDisplaySeverity(room))}" data-room="${escapeHtml(room.roomId || "")}" data-device="${escapeHtml(room.deviceKey || "")}">
            <div class="room-card-head">
              <span><small>${escapeHtml(room.sectionLabel || room.sectionKey || "Solrom")}</small><strong>${escapeHtml(room.title || room.roomLabel || room.roomId || "Rom")}</strong></span>
              <b>${escapeHtml(severityLabel(roomDisplaySeverity(room)))}</b>
            </div>
            <p>${escapeHtml(doorSessionSummary(room))}</p>
            <footer><span>${escapeHtml(roomDisplayLabel(room))}</span><time>${escapeHtml(room.doorChangedLabel || room.lastChangedLabel || "-")}</time></footer>
          </article>
        `).join("") || '<p class="empty-state">Ingen romdata er tilgjengelig.</p>'}
      </div>
    </section>

    <section class="section-block">
      <div class="section-title"><h2>Alarmhistorikk</h2><span>${history.length}</span></div>
      <div class="event-list door-history">
        ${history.slice(0, 80).map((item) => `
          <article id="alarm-${escapeHtml(item.id)}" class="history-row ${severityClass(item.status === "active" ? "alert" : "resolved")}" data-alarm-key="${escapeHtml(item.eventKey || "")}">
            <span class="event-marker ${item.status === "active" ? "is-alert" : "is-ok"}"></span>
            <span><small>${escapeHtml(item.status === "active" ? "Pågår" : `Løst ${item.resolvedLabel || ""}`)}</small><strong>${escapeHtml(item.title || "Døralarm")}</strong><em>${escapeHtml(item.detail || "")}</em></span>
            <time>${escapeHtml(item.detectedLabel || formatStamp(item.detectedAt))}</time>
          </article>
        `).join("") || '<p class="empty-state">Ingen døralarmer er lagret.</p>'}
      </div>
    </section>
  `;
}

function monitorStatus(item) {
  const normalized = text(item.status).toLowerCase();
  if (normalized === "normal") return ["Normal", "is-ok"];
  if (normalized === "suspected") return ["Mulig endring", "is-warning"];
  if (["changed", "obscured"].includes(normalized)) return [normalized === "changed" ? "Endring" : "Tildekket", "is-warning"];
  if (["error", "uncalibrated"].includes(normalized)) return [normalized === "error" ? "Feil" : "Mangler referanse", "is-alert"];
  return [severityLabel(normalized), "is-neutral"];
}

function changeScoreLabel(item) {
  return item?.changeScore === null || item?.changeScore === undefined
    ? "Ikke beregnet"
    : `${Math.round(number(item.changeScore) * 100)} %`;
}

function imageTime(value) {
  return value ? formatStamp(value, true) : "Ikke tilgjengelig";
}

function monitorCard(item, { detail = false } = {}) {
  const images = item.images || {};
  const canCompare = Boolean(images.baseline && images.latest);
  const [label, statusClass] = monitorStatus(item);
  const aspect = Math.max(0.45, Math.min(3, number(item.crop?.aspectRatio) || 16 / 9));
  return `
    <article class="camera-card ${detail ? "is-detail" : ""}" data-monitor="${escapeHtml(item.id)}" data-mode="${canCompare ? "compare" : "latest"}">
      ${detail ? "" : `<header><span><small>${item.kind === "stairs" ? "Trapp" : "Pullert"}</small><strong>${escapeHtml(item.name)}</strong></span><b class="status-chip ${statusClass}">${escapeHtml(label)}</b></header>`}
      <div class="image-modes" role="group" aria-label="Bildevisning">
        ${canCompare ? '<button type="button" class="is-active" data-image-mode="compare">Gjennomsiktig</button>' : ""}
        ${images.latest ? '<button type="button" data-image-mode="latest">Siste</button>' : ""}
        ${images.overlay ? '<button type="button" data-image-mode="overlay">Forskjell</button>' : ""}
        ${images.baseline ? '<button type="button" data-image-mode="baseline">Referanse</button>' : ""}
      </div>
      ${images.baseline || images.latest ? `
        <div class="image-compare" style="--image-aspect:${aspect}">
          <img class="base-image" src="${escapeHtml(canCompare ? images.baseline : images.latest)}" alt="Kontrollbilde fra ${escapeHtml(item.name)}" loading="lazy">
          <div class="latest-layer" style="opacity:.5"><img class="latest-image" src="${escapeHtml(images.latest || images.baseline)}" alt="Siste bilde fra ${escapeHtml(item.name)}" loading="lazy"></div>
          <span class="reference-label">Referanse</span><span class="latest-label">Siste</span>
        </div>
        <div class="compare-footer">
          <time>${escapeHtml(imageTime(item.baselineCapturedAt))}</time>
          <label><span>50 %</span><input type="range" min="0" max="100" value="50" aria-label="Gjennomsiktighet"></label>
          <time>${escapeHtml(imageTime(item.latestCapturedAt))}</time>
        </div>
      ` : '<p class="empty-state">Ingen bilder tilgjengelig.</p>'}
      ${item.lastError ? `<p class="inline-error">${escapeHtml(item.lastError)}</p>` : ""}
    </article>
  `;
}

function monitorSummaryCard(item) {
  const images = item.images || {};
  const preview = images.latest || images.baseline;
  const [label, statusClass] = monitorStatus(item);
  return `
    <button class="monitor-summary-card" type="button" data-monitor-open="${escapeHtml(item.id)}">
      <span class="monitor-preview">
        ${preview ? `<img src="${escapeHtml(preview)}" alt="Siste kontrollbilde fra ${escapeHtml(item.name)}" loading="lazy">` : '<span>Ingen bilde</span>'}
      </span>
      <span class="monitor-summary-copy">
        <small>${item.kind === "stairs" ? "Trapp" : "Pullertfelt"}</small>
        <strong>${escapeHtml(item.name)}</strong>
        <time>${escapeHtml(imageTime(item.latestCapturedAt || item.baselineCapturedAt))}</time>
      </span>
      <span class="monitor-summary-state"><b class="status-chip ${statusClass}">${escapeHtml(label)}</b><i aria-hidden="true">›</i></span>
    </button>
  `;
}

function incidentMatchesMonitor(incident, monitor) {
  const key = text(incident?.bollard_key).toLowerCase();
  const displayName = text(incident?.display_name).toLowerCase();
  const monitorName = text(monitor?.name).toLowerCase();
  if (monitor?.assetKey && key === text(monitor.assetKey).toLowerCase()) return true;
  if (incident?.camera_id && String(incident.camera_id) === String(monitor?.cameraId)) return true;
  if (displayName && monitorName && (displayName.includes(monitorName) || monitorName.includes(displayName))) return true;
  if (monitor?.kind === "stairs") return key.includes("trapp");
  return monitorName.includes("solstudio front") && key === "pullertomrade-solstudio";
}

function incidentRows(incidents) {
  if (!incidents.length) return '<p class="empty-state">Ingen hendelser er knyttet til dette kontrollfeltet.</p>';
  return incidents.slice(0, 40).map((item) => `
    <article id="incident-${escapeHtml(item.incident_id)}" class="history-row ${severityClass(item.status)}">
      <span class="event-marker ${["active", "acknowledged"].includes(text(item.status).toLowerCase()) ? "is-alert" : "is-ok"}"></span>
      <span><small>${escapeHtml(severityLabel(item.status))}</small><strong>${escapeHtml(item.display_name || item.bollard_key || "Kamerahendelse")}</strong><em>${escapeHtml(text(item.notification_status) === "sent" ? "Varsel sendt" : "Registrert av kamerakontrollen")}</em></span>
      <time>${escapeHtml(formatStamp(item.detected_at))}</time>
    </article>
  `).join("");
}

function openBollardDetail(monitorId, { replace = false } = {}) {
  if (!monitorId) return;
  state.currentMonitorId = String(monitorId);
  renderBollardDetail();
  showView("bollardDetail", { updateUrl: false });
  const url = new URL(window.location.href);
  url.searchParams.set("section", "pullerter");
  url.searchParams.set("monitor", state.currentMonitorId);
  url.searchParams.delete("incident");
  window.history[replace ? "replaceState" : "pushState"]({}, "", `${url.pathname}${url.search}`);
}

function renderBollardDetail() {
  const root = $("#bollardDetailView");
  if (!root) return;
  const monitors = state.data?.bollards?.monitors || [];
  const monitorId = state.currentMonitorId || monitorIdFromUrl();
  const index = monitors.findIndex((item) => String(item.id) === String(monitorId));
  const item = index >= 0 ? monitors[index] : null;
  if (!item) {
    root.innerHTML = `
      <button class="detail-back-button" type="button" data-back-to-monitors>‹ <span>Kontrollbilder</span></button>
      <section class="section-block"><p class="empty-state">Kontrollbildet finnes ikke lenger.</p></section>
    `;
    $("[data-back-to-monitors]", root)?.addEventListener("click", () => showView("bollards"));
    return;
  }
  state.currentMonitorId = String(item.id);
  const [statusLabel, statusClass] = monitorStatus(item);
  const relatedIncidents = (state.data?.bollards?.incidents || []).filter((incident) => incidentMatchesMonitor(incident, item));
  const previous = monitors[(index - 1 + monitors.length) % monitors.length];
  const next = monitors[(index + 1) % monitors.length];
  root.innerHTML = `
    <div class="detail-toolbar">
      <button class="detail-back-button" type="button" data-back-to-monitors>‹ <span>Kontrollbilder</span></button>
      <div class="monitor-pager" aria-label="Bytt kontrollbilde">
        <button type="button" data-monitor-page="${escapeHtml(previous?.id || item.id)}" aria-label="Forrige kontrollbilde">‹</button>
        <span>${index + 1} av ${monitors.length}</span>
        <button type="button" data-monitor-page="${escapeHtml(next?.id || item.id)}" aria-label="Neste kontrollbilde">›</button>
      </div>
    </div>
    <section class="view-head monitor-detail-head">
      <div><p class="eyebrow">${item.kind === "stairs" ? "Trapp" : "Pullertfelt"}</p><h1>${escapeHtml(item.name)}</h1></div>
      <span class="count-badge ${statusClass}">${escapeHtml(statusLabel)}</span>
    </section>
    <section class="monitor-detail-metrics">
      <div><small>Siste bilde</small><strong>${escapeHtml(imageTime(item.latestCapturedAt))}</strong></div>
      <div><small>Sist kontrollert</small><strong>${escapeHtml(imageTime(item.lastCheckedAt))}</strong></div>
      <div><small>Endringsscore</small><strong>${escapeHtml(changeScoreLabel(item))}</strong></div>
    </section>
    ${monitorCard(item, { detail: true })}
    <section class="section-block">
      <div class="section-title"><h2>Hendelser for feltet</h2><span>${relatedIncidents.length}</span></div>
      <div class="event-list">${incidentRows(relatedIncidents)}</div>
    </section>
  `;
  $("[data-back-to-monitors]", root)?.addEventListener("click", () => showView("bollards"));
  $$('[data-monitor-page]', root).forEach((button) => button.addEventListener("click", () => openBollardDetail(button.dataset.monitorPage, { replace: true })));
  bindCameraControls(root);
}

function renderBollards() {
  const root = $("#bollardsView");
  if (!root) return;
  const payload = state.data?.bollards || {};
  const summary = payload.summary || {};
  const incidents = payload.incidents || [];
  const monitors = payload.monitors || [];
  const channel = subscription("bollards");
  root.innerHTML = `
    <section class="view-head">
      <div><p class="eyebrow">Kamerakontroll</p><h1>Pullerter og trapp</h1></div>
      <span class="count-badge ${number(summary.active_incidents) ? "is-alert" : "is-ok"}">${number(summary.active_incidents)} aktive</span>
    </section>
    <section class="metric-strip is-three">
      <div><small>Kontrollfelt</small><strong>${number(summary.inspection_objects)}</strong></div>
      <div><small>Kalibrert</small><strong>${number(summary.baseline_cameras) + number(summary.calibrated_assets)}</strong></div>
      <div><small>AI-avvik</small><strong>${number(summary.ai_anomalies)}</strong></div>
    </section>
    <section class="channel-row">
      <span><strong>Pullertvarsler i ntfy</strong><small>${channel.publishingEnabled ? "Varsling er aktiv" : "Kontroller abonnementet"}</small></span>
      <div class="channel-actions">${channel.subscribeUrl ? `<a href="${escapeHtml(channel.subscribeUrl)}">Abonner</a>` : ""}<button id="testBollardButton" type="button">Test</button></div>
    </section>
    <section class="section-block camera-section">
      <div class="section-title"><h2>Kontrollbilder</h2><span>${monitors.length}</span></div>
      <div class="monitor-list">${monitors.map(monitorSummaryCard).join("") || '<p class="empty-state">Ingen kontrollbilder er tilgjengelig.</p>'}</div>
    </section>
    <section class="section-block">
      <div class="section-title"><h2>Hendelser</h2><span>${incidents.length}</span></div>
      <div class="event-list">${incidentRows(incidents)}</div>
    </section>
  `;
  $$('[data-monitor-open]', root).forEach((button) => button.addEventListener("click", () => openBollardDetail(button.dataset.monitorOpen)));
  $("#testBollardButton", root)?.addEventListener("click", sendBollardTest);
}

function renderAccount() {
  const root = $("#accountView");
  if (!root) return;
  const user = state.data?.user || {};
  const username = text(user.username, "Bruker");
  const initial = username.slice(0, 1).toUpperCase();
  root.innerHTML = `
    <section class="view-head"><div><p class="eyebrow">Lilletorget</p><h1>Konto</h1></div></section>
    <section class="account-card">
      <span class="account-initial">${escapeHtml(initial)}</span>
      <div><strong>${escapeHtml(user.displayName || user.name || username)}</strong><small>${escapeHtml(username)}</small></div>
    </section>
    <dl class="account-details">
      <div><dt>Rolle</dt><dd>${escapeHtml(user.role || (user.isMaster ? "Master" : "Bruker"))}</dd></div>
      <div><dt>Alarm-build</dt><dd>${escapeHtml(state.data?.build || "-")}</dd></div>
      <div><dt>Sist oppdatert</dt><dd>${escapeHtml(formatStamp(state.data?.generatedAt, true))}</dd></div>
    </dl>
    <button class="appkit-theme-setting" type="button" data-toggle-theme>
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 15.2A8.5 8.5 0 0 1 8.8 4a7.8 7.8 0 1 0 11.2 11.2Z"/></svg>
      <span><strong>Utseende</strong><small data-theme-label>${document.documentElement.dataset.theme === "dark" ? "Lyst tema" : "Mørkt tema"}</small></span>
    </button>
    <form method="post" action="/konto/logg-ut"><button class="logout-button" type="submit">Logg ut</button></form>
  `;
}

function bindCameraControls(root) {
  $$('[data-image-mode]', root).forEach((button) => {
    button.addEventListener("click", () => {
      const card = button.closest(".camera-card");
      const item = (state.data?.bollards?.monitors || []).find((row) => String(row.id) === String(card?.dataset.monitor));
      if (!card || !item) return;
      const mode = button.dataset.imageMode;
      card.dataset.mode = mode;
      $$('[data-image-mode]', card).forEach((entry) => entry.classList.toggle("is-active", entry === button));
      const base = $(".base-image", card);
      const layer = $(".latest-layer", card);
      const latest = $(".latest-image", card);
      const footer = $(".compare-footer", card);
      if (!base || !layer || !latest) return;
      if (mode === "compare") {
        base.src = item.images.baseline;
        latest.src = item.images.latest;
        layer.classList.remove("is-hidden");
        footer?.classList.remove("is-hidden");
      } else {
        base.src = item.images[mode] || item.images.latest || item.images.baseline;
        layer.classList.add("is-hidden");
        footer?.classList.add("is-hidden");
      }
    });
  });
  $$('.compare-footer input[type="range"]', root).forEach((input) => {
    input.addEventListener("input", () => {
      const card = input.closest(".camera-card");
      const layer = $(".latest-layer", card);
      const label = $(".compare-footer label span", card);
      if (layer) layer.style.opacity = String(number(input.value) / 100);
      if (label) label.textContent = `${input.value} %`;
    });
  });
}

async function sendBollardTest(event) {
  const button = event.currentTarget;
  button.disabled = true;
  setMessage("Sender testvarsel …");
  try {
    const response = await fetch("/api/notifications/bollards/test", { method: "POST", credentials: "same-origin" });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.detail || "Kunne ikke sende testvarsel.");
    setMessage("Testvarselet er sendt til ntfy.");
  } catch (error) {
    setMessage(error.message || String(error), true);
  } finally {
    button.disabled = false;
  }
}

function openTarget(target) {
  const [view, id] = String(target || "").split(":", 2);
  showView(view);
  window.setTimeout(() => {
    const selector = view === "bollards" ? `#incident-${CSS.escape(id)}` : `[data-device="${CSS.escape(id)}"]`;
    const element = $(selector);
    element?.scrollIntoView({ behavior: "smooth", block: "center" });
    element?.classList.add("is-highlighted");
    window.setTimeout(() => element?.classList.remove("is-highlighted"), 2400);
  }, 50);
}

function renderAll() {
  renderOverview();
  renderDoors();
  renderBollards();
  renderBollardDetail();
  renderAccount();
  const updated = $("#lastUpdated");
  if (updated) updated.textContent = `Oppdatert ${formatAge(state.data?.generatedAt)}`;
}

function focusDeepLink() {
  const params = new URLSearchParams(window.location.search);
  const alarmId = params.get("alarm");
  const incidentId = params.get("incident");
  const target = alarmId ? $(`#alarm-${CSS.escape(alarmId)}`) : incidentId ? $(`#incident-${CSS.escape(incidentId)}`) : null;
  if (target) {
    target.scrollIntoView({ behavior: "smooth", block: "center" });
    target.classList.add("is-highlighted");
  }
}

async function loadData({ quiet = false } = {}) {
  if (state.busy) return;
  state.busy = true;
  $("#refreshButton")?.classList.add("is-spinning");
  if (!quiet) setMessage("Henter alarmstatus …");
  try {
    const response = await fetch("/api/bootstrap", { credentials: "same-origin", cache: "no-store" });
    if (response.status === 401) {
      const next = encodeURIComponent(`${window.location.pathname}${window.location.search}`);
      window.location.assign(`/auth/login?next=${next}`);
      return;
    }
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.detail || "Kunne ikke hente alarmstatus.");
    state.data = payload;
    renderAll();
    showView(state.currentView, { updateUrl: false });
    setMessage("");
    window.setTimeout(focusDeepLink, 80);
  } catch (error) {
    setMessage(error.message || String(error), true);
  } finally {
    state.busy = false;
    $("#refreshButton")?.classList.remove("is-spinning");
  }
}

document.addEventListener("DOMContentLoaded", async () => {
  state.currentMonitorId = monitorIdFromUrl();
  state.currentView = routeFromUrl();
  $$('[data-view]').forEach((button) => button.addEventListener("click", () => showView(button.dataset.view)));
  $("#refreshButton")?.addEventListener("click", () => loadData());
  window.addEventListener("popstate", () => {
    state.currentMonitorId = monitorIdFromUrl();
    showView(routeFromUrl(), { updateUrl: false });
    if (state.currentView === "bollardDetail") renderBollardDetail();
    focusDeepLink();
  });
  document.addEventListener("keydown", (event) => {
    if (!['+', '-', '='].includes(event.key)) return;
    const visibleCard = $("#bollardDetailView:not(.is-hidden) .camera-card[data-mode='compare']");
    const slider = visibleCard ? $('input[type="range"]', visibleCard) : null;
    if (!slider) return;
    event.preventDefault();
    const delta = event.key === '-' ? -5 : 5;
    slider.value = String(Math.max(0, Math.min(100, number(slider.value) + delta)));
    slider.dispatchEvent(new Event("input"));
  });
  await loadData();
  window.setInterval(() => loadData({ quiet: true }), 60_000);
});
