const state = {
  overview: null,
  catalog: null,
  storage: null,
  events: null,
  recognitions: null,
  plates: null,
  recognitionSummary: null,
  integrationStatus: null,
  bollards: null,
  bollardDrawing: null,
  builds: null,
  eventOffset: 0,
  pageSize: 50,
};

const pageMeta = {
  dashboard: ["UniFi Protect", "Driftsoversikt"],
  events: ["Hendelsesarkiv", "Hendelser"],
  recognitions: ["Lokal AI-metadata", "Gjenkjenning"],
  plates: ["Renset skiltlogg", "Biler"],
  bollards: ["Lokal områdekontroll", "Pullerter"],
  configuration: ["Lagringspolicy", "Innstillinger"],
  storage: ["PostgreSQL", "Lagring"],
  integrations: ["Lokalt API", "Integrasjoner"],
  builds: ["Versjon og historikk", "Buildlogg"],
};

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const number = (value) => new Intl.NumberFormat("nb-NO").format(Number(value || 0));
const dateTime = (value) => value ? new Intl.DateTimeFormat("nb-NO", { dateStyle: "short", timeStyle: "medium" }).format(new Date(value)) : "–";
const shortDate = (value) => value ? new Intl.DateTimeFormat("nb-NO", { day: "2-digit", month: "short" }).format(new Date(value)) : "–";
const duration = (ms) => {
  if (ms === null || ms === undefined) return "Pågår";
  if (ms < 1000) return `${ms} ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(ms < 10000 ? 1 : 0)} sek`;
  return `${Math.floor(ms / 60000)}m ${Math.round((ms % 60000) / 1000)}s`;
};
const bytes = (value) => {
  let n = Number(value || 0);
  const units = ["B", "KB", "MB", "GB", "TB"];
  let index = 0;
  while (n >= 1024 && index < units.length - 1) { n /= 1024; index += 1; }
  return `${n.toLocaleString("nb-NO", { maximumFractionDigits: index ? 1 : 0 })} ${units[index]}`;
};
const escapeHtml = (value) => String(value ?? "").replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[char]));

async function api(url, options = {}) {
  const response = await fetch(url, { headers: { "Content-Type": "application/json", ...(options.headers || {}) }, ...options });
  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try { detail = (await response.json()).detail || detail; } catch (_) {}
    throw new Error(detail);
  }
  if (response.status === 204) return null;
  return response.json();
}

let toastTimer;
function toast(message, error = false) {
  const element = $("#toast");
  clearTimeout(toastTimer);
  element.textContent = message;
  element.classList.toggle("error", error);
  element.hidden = false;
  toastTimer = setTimeout(() => { element.hidden = true; }, 3600);
}

function currentPage() {
  if (location.pathname.startsWith("/events")) return "events";
  if (location.pathname.startsWith("/recognitions")) return "recognitions";
  if (location.pathname.startsWith("/plates")) return "plates";
  if (location.pathname.startsWith("/bollards")) return "bollards";
  if (location.pathname.startsWith("/configuration")) return "configuration";
  if (location.pathname.startsWith("/storage")) return "storage";
  if (location.pathname.startsWith("/integrations")) return "integrations";
  if (location.pathname.startsWith("/builds")) return "builds";
  return "dashboard";
}

function setPage(page) {
  $$('[data-page]').forEach((element) => { element.hidden = element.dataset.page !== page; });
  let activeRoute = null;
  $$('[data-route]').forEach((element) => {
    const active = element.dataset.route === page;
    element.classList.toggle("active", active);
    if (active) activeRoute = element;
  });
  if (activeRoute && window.matchMedia("(max-width: 600px)").matches) {
    requestAnimationFrame(() => activeRoute.scrollIntoView({ block: "nearest", inline: "nearest" }));
  }
  const [eyebrow, title] = pageMeta[page];
  $("#page-eyebrow").textContent = eyebrow;
  $("#page-title").textContent = title;
}

function setConnection(health = {}) {
  const connected = Boolean(health.websocket_connected);
  const pill = $("#connection-pill");
  pill.classList.toggle("online", connected);
  pill.classList.toggle("offline", !connected);
  pill.innerHTML = `<span></span>${connected ? "WebSocket tilkoblet" : "Kobler opp igjen"}`;
  const dot = $("#sidebar-status-dot");
  dot.classList.toggle("online", connected);
  dot.classList.toggle("offline", !connected);
  $("#sidebar-status-text").textContent = connected ? "Sanntid aktiv" : "Midlertidig frakoblet";
  $("#sidebar-console").textContent = health.console_key || "UniFi Protect";
  const appBuild = health.app || { version: health.version, build: health.build };
  $("#sidebar-build-number").textContent = appBuild.build
    ? `v${appBuild.version || "1"} · build ${appBuild.build}`
    : "Build –";
}

function buildList(values) {
  if (!values?.length) return '<li class="muted-item">Ingen oppføringer.</li>';
  return values.map((value) => `<li>${escapeHtml(value)}</li>`).join("");
}

function buildEntry(row, currentBuild) {
  const isCurrent = String(row.build) === String(currentBuild);
  return `<details class="build-entry ${isCurrent ? "current" : ""}" ${isCurrent ? "open" : ""}>
    <summary>
      <span class="build-index"><small>Build</small><strong>${escapeHtml(row.build)}</strong></span>
      <span class="build-summary-copy"><strong>${escapeHtml(row.headline)}</strong><small>${escapeHtml(row.title)}</small></span>
      <span class="build-summary-meta"><strong>${escapeHtml(row.date)}</strong><small>Versjon ${escapeHtml(row.version)}</small></span>
    </summary>
    <div class="build-detail">
      <p>${escapeHtml(row.description)}</p>
      ${row.request ? `<blockquote><span>Bestilling</span>${escapeHtml(row.request)}</blockquote>` : ""}
      <div class="build-detail-grid">
        <section><h3>Levert</h3><ul>${buildList(row.changes)}</ul></section>
        <section><h3>Berørte komponenter</h3><ul class="component-list">${buildList(row.applications)}</ul></section>
      </div>
    </div>
  </details>`;
}

async function loadBuilds() {
  const query = $("#build-query").value.trim();
  const data = await api(`/api/builds?q=${encodeURIComponent(query)}&limit=100`);
  state.builds = data;
  const current = data.current || {};
  const latest = data.latest;
  $("#build-current-badge").textContent = `Build ${current.build || "–"}`;
  $("#build-current-version").textContent = `Versjon ${current.version || "–"}`;
  $("#build-version").textContent = current.version || "–";
  $("#build-number").textContent = current.build || "–";
  $("#build-count").textContent = number(data.total_count);
  $("#build-latest-date").textContent = latest?.date || "–";
  $("#build-latest-headline").textContent = query
    ? `${number(data.count)} treff for «${query}»`
    : latest?.headline || "Ingen loggførte builds";
  $("#build-list").innerHTML = data.items?.length
    ? data.items.map((row) => buildEntry(row, current.build)).join("")
    : '<div class="panel build-empty"><strong>Ingen treff</strong><p>Prøv et annet søkeord eller nullstill filteret.</p></div>';
}

function tags(values) {
  if (!values?.length) return '<span class="tag muted">Ingen undertype</span>';
  return values.map((value) => `<span class="tag ${String(value).startsWith("alrm") ? "audio" : ""}">${escapeHtml(displayDetection(value))}</span>`).join("");
}

function displayDetection(value) {
  const match = state.catalog?.detection_types?.find((item) => item.detection_type === value);
  return match?.display_name || value;
}

function eventRow(row, detailButton = false) {
  return `<tr>
    <td class="snapshot-cell">${snapshotPreview(row)}</td>
    <td class="event-time"><strong>${dateTime(row.start_at || row.last_received_at)}</strong><small>${escapeHtml(row.source_event_id?.slice(0, 16) || "")}</small></td>
    <td>${escapeHtml(row.camera_name || row.camera_id || "Ukjent kamera")}</td>
    <td><strong>${escapeHtml(row.event_type || "Ukjent")}</strong></td>
    <td><div class="tag-list">${tags(row.smart_detect_types)}</div></td>
    <td>${duration(row.duration_ms)}</td>
    ${detailButton ? `<td>${number(row.update_count)}</td><td><button class="secondary-button event-detail" data-event-id="${escapeHtml(row.source_event_id)}" type="button">Detaljer</button></td>` : ""}
  </tr>`;
}

function snapshotPreview(row) {
  if (row.snapshot_status === "stored") {
    const source = `/api/events/${encodeURIComponent(row.source_event_id)}/snapshot`;
    return `<button class="snapshot-button event-detail" data-event-id="${escapeHtml(row.source_event_id)}" type="button" aria-label="Vis stillbilde"><img src="${source}" alt="" loading="lazy"></button>`;
  }
  const labels = { pending: "Venter", capturing: "Henter", failed: "Feil", not_requested: "Av" };
  return `<span class="snapshot-state ${escapeHtml(row.snapshot_status || "not_requested")}">${labels[row.snapshot_status] || "–"}</span>`;
}

async function loadOverview() {
  const data = await api("/api/overview");
  state.overview = data;
  setConnection(data.health);
  const totals = data.totals || {};
  const cameras = data.cameras || {};
  const catalog = data.catalog || {};
  $("#metric-events").textContent = number(totals.event_count);
  $("#metric-events-hour").textContent = `${number(totals.events_1h)} siste time`;
  $("#metric-24h").textContent = number(totals.events_24h);
  $("#metric-ignored").textContent = `${number(catalog.ignored_messages)} filtrert bort`;
  $("#metric-cameras").textContent = `${number(cameras.connected_cameras)} / ${number(cameras.camera_count)}`;
  $("#metric-enabled-cameras").textContent = `${number(cameras.enabled_cameras)} aktive for lagring`;
  $("#metric-types").textContent = number(catalog.observed_types);
  $("#metric-catalog").textContent = `${number(catalog.catalog_types)} hovedtyper i katalogen`;
  $("#hero-last-event").textContent = totals.last_event_at ? dateTime(totals.last_event_at) : "Venter på hendelse";
  renderDaily(data.daily || []);
  renderTypeSummary(data.event_types || []);
  $("#recent-events-body").innerHTML = data.recent?.length ? data.recent.map((row) => eventRow(row)).join("") : '<tr class="empty-row"><td colspan="6">Ingen lagrede hendelser ennå.</td></tr>';
}

function renderDaily(rows) {
  const byDay = new Map(rows.map((row) => [String(row.day).slice(0, 10), Number(row.count)]));
  const values = [];
  for (let index = 13; index >= 0; index -= 1) {
    const day = new Date();
    day.setHours(0, 0, 0, 0);
    day.setDate(day.getDate() - index);
    const key = day.toISOString().slice(0, 10);
    values.push({ day, count: byDay.get(key) || 0 });
  }
  const max = Math.max(1, ...values.map((item) => item.count));
  $("#daily-chart").innerHTML = values.map((item) => `<div class="bar-column" title="${number(item.count)} hendelser ${shortDate(item.day)}"><span class="bar-value">${item.count || ""}</span><span class="bar-track"><span class="bar-fill" style="height:${Math.max(item.count ? 4 : 0, (item.count / max) * 100)}%"></span></span><span class="bar-label">${shortDate(item.day)}</span></div>`).join("");
}

function renderTypeSummary(rows) {
  const visible = rows.slice(0, 7);
  $("#type-summary").innerHTML = visible.length ? visible.map((row) => `<div class="summary-row"><div><strong>${escapeHtml(row.event_type)}</strong><small>${escapeHtml(row.category)} · ${row.store_enabled ? "lagres" : "ignoreres"}</small></div><span class="summary-count">${number(row.observed_count)}</span></div>`).join("") : '<p class="quiet-label">Katalogen fylles når strømmen starter.</p>';
}

function toggle(kind, key, checked, label) {
  return `<button class="switch rule-toggle" type="button" role="switch" aria-checked="${checked}" aria-label="${escapeHtml(label)}" data-kind="${escapeHtml(kind)}" data-key="${escapeHtml(key)}"></button>`;
}

async function loadCatalog() {
  const data = await api("/api/catalog");
  state.catalog = data;
  const settings = data.settings || {};
  $("#setting-default-store").value = String(Boolean(settings.default_store_new_event_types));
  $("#setting-retention-days").value = settings.retention_days || 365;
  $("#setting-sample-limit").value = String(settings.catalog_sample_limit_bytes || 65536);
  $("#setting-snapshots-enabled").value = String(settings.snapshots_enabled !== false);
  $("#setting-snapshot-quality").value = String(Boolean(settings.snapshot_high_quality));
  $("#setting-snapshot-max").value = String(settings.snapshot_max_bytes || 12582912);
  renderEventTypeConfig(data.event_types || []);
  renderDetectionConfig(data.detection_types || []);
  renderCameraConfig(data.cameras || []);
  populateFilters(data);
  const enabled = [...(data.event_types || []), ...(data.detection_types || []), ...(data.cameras || [])].filter((item) => item.store_enabled).length;
  $("#config-enabled-count").textContent = number(enabled);
}

function renderEventTypeConfig(rows) {
  $("#event-type-count").textContent = `${number(rows.length)} typer`;
  $("#event-type-config").innerHTML = rows.map((row) => `<div class="config-item"><div class="config-item-main"><strong>${escapeHtml(row.event_type)} <span class="${row.is_observed ? "observed-badge" : "possible-badge"}">${row.is_observed ? "Observert" : "Forberedt"}</span></strong><p>${escapeHtml(row.description || "")}</p><div class="config-meta"><span>${escapeHtml(row.category)}</span><span>${number(row.observed_count)} meldinger</span><span>${number(row.ignored_count)} filtrert</span></div></div>${toggle("event_type", row.event_type, row.store_enabled, `Lagre ${row.event_type}`)}</div>`).join("");
}

function renderDetectionConfig(rows) {
  $("#detection-type-count").textContent = `${number(rows.length)} muligheter`;
  const groups = ["Objekt", "Lyd", "Annet"];
  $("#detection-type-config").innerHTML = groups.map((category) => {
    const items = rows.filter((row) => row.category === category || (category === "Annet" && !groups.slice(0, 2).includes(row.category)));
    if (!items.length) return "";
    return `<section class="detection-group"><h4>${category}</h4>${items.map((row) => `<div class="config-item"><div class="config-item-main"><strong>${escapeHtml(row.display_name)} ${row.is_observed ? '<span class="observed-badge">Observert</span>' : '<span class="possible-badge">Mulig</span>'}</strong><p>${escapeHtml(row.description || "")}</p><div class="config-meta"><span>${number(row.supported_camera_count)} kameraer</span><span>${number(row.observed_count)} meldinger</span><span>${escapeHtml(row.detection_type)}</span></div></div>${toggle("detection_type", row.detection_type, row.store_enabled, `Lagre ${row.display_name}`)}</div>`).join("")}</section>`;
  }).join("");
}

function renderCameraConfig(rows) {
  $("#camera-config").innerHTML = rows.map((camera) => {
    const capabilityCount = (camera.smart_detect_types?.length || 0) + (camera.smart_detect_audio_types?.length || 0);
    const online = camera.state === "CONNECTED";
    return `<article class="camera-card"><div><strong>${escapeHtml(camera.name || camera.camera_id)}</strong><p>${escapeHtml(camera.model_key || "UniFi-kamera")} · ${capabilityCount} AI-/lydmuligheter</p><span class="camera-status ${online ? "" : "offline"}">${online ? "Tilkoblet" : escapeHtml(camera.state || "Ukjent")}</span><div class="config-meta"><span>${number(camera.observed_event_count)} meldinger</span><span>Sist ${dateTime(camera.last_event_at)}</span></div></div>${toggle("camera", camera.camera_id, camera.store_enabled, `Lagre hendelser fra ${camera.name || camera.camera_id}`)}</article>`;
  }).join("");
}

function populateFilters(data) {
  const selected = {
    event: $("#filter-event-type").value,
    detection: $("#filter-detection-type").value,
    camera: $("#filter-camera").value,
  };
  $("#filter-event-type").innerHTML = '<option value="">Alle hendelser</option>' + data.event_types.map((row) => `<option value="${escapeHtml(row.event_type)}">${escapeHtml(row.event_type)}</option>`).join("");
  $("#filter-detection-type").innerHTML = '<option value="">Alle deteksjoner</option>' + data.detection_types.map((row) => `<option value="${escapeHtml(row.detection_type)}">${escapeHtml(row.display_name)}</option>`).join("");
  $("#filter-camera").innerHTML = '<option value="">Alle kameraer</option>' + data.cameras.map((row) => `<option value="${escapeHtml(row.camera_id)}">${escapeHtml(row.name || row.camera_id)}</option>`).join("");
  $("#filter-event-type").value = selected.event;
  $("#filter-detection-type").value = selected.detection;
  $("#filter-camera").value = selected.camera;
  const recognitionCamera = $("#recognition-filter-camera");
  const recognitionSelected = recognitionCamera.value;
  recognitionCamera.innerHTML = '<option value="">Alle kameraer</option>' + data.cameras.map((row) => `<option value="${escapeHtml(row.camera_id)}">${escapeHtml(row.name || row.camera_id)}</option>`).join("");
  recognitionCamera.value = recognitionSelected;
}

function recognitionKind(kind) {
  return { license_plate: "Bilskilt", face: "Ansikt", person_of_interest: "Person av interesse" }[kind] || kind || "Ukjent";
}

function recognitionRow(row) {
  const known = row.is_known === true ? '<span class="recognition-badge known">Kjent</span>' : row.is_known === false ? '<span class="recognition-badge unknown">Ukjent</span>' : '<span class="recognition-badge neutral">Uavklart</span>';
  const value = row.value || (row.kind === "license_plate" ? "Skiltverdi ikke sendt" : "Navn ikke sendt");
  const imageOffset = Number(row.snapshot_time_offset_ms);
  const imageState = row.snapshot_status === "stored" ? `<span class="recognition-badge ${Number.isFinite(imageOffset) && Math.abs(imageOffset) <= 1500 ? "known" : "pending"}">Bilde ${Number.isFinite(imageOffset) ? `${imageOffset >= 0 ? "+" : ""}${(imageOffset / 1000).toFixed(2)} s` : "lagret"}</span>` : row.snapshot_status === "pending" || row.snapshot_status === "capturing" ? '<span class="recognition-badge pending">Henter bilde</span>' : '<span class="recognition-badge neutral">Uten bilde</span>';
  const detail = `${imageState}<button class="secondary-button recognition-detail" data-recognition-id="${escapeHtml(row.recognition_id)}" type="button">Detaljer</button>`;
  return `<tr><td class="event-time"><strong>${dateTime(row.occurred_at)}</strong><small>${escapeHtml(String(row.recognition_id || ""))}</small></td><td><span class="tag">${escapeHtml(recognitionKind(row.kind))}</span></td><td><strong class="recognition-value">${escapeHtml(value)}</strong></td><td>${known}</td><td>${escapeHtml(row.camera_name || row.camera_id || "Ukjent kamera")}</td><td>${detail}</td></tr>`;
}

async function loadRecognitions() {
  const known = $("#recognition-filter-known").value;
  const params = new URLSearchParams({
    kind: $("#recognition-filter-kind").value,
    value: $("#recognition-filter-value").value,
    camera_id: $("#recognition-filter-camera").value,
    limit: "200",
  });
  if (known) params.set("is_known", known);
  const [summary, data] = await Promise.all([
    api("/api/recognition-summary"),
    api(`/api/recognitions?${params}`),
  ]);
  state.recognitionSummary = summary;
  state.recognitions = data;
  const totals = summary.totals || {};
  $("#recognition-total").textContent = number(totals.total);
  $("#recognition-24h").textContent = `${number(totals.last_24h)} siste døgn`;
  $("#recognition-plates").textContent = number(totals.license_plates);
  $("#recognition-faces").textContent = number(totals.faces);
  $("#recognition-unique").textContent = number(totals.unique_values);
  $("#recognition-known").textContent = `${number(totals.known)} kjente · ${number(totals.unknown)} ukjente`;
  $("#recognition-last").textContent = totals.last_recognition_at ? dateTime(totals.last_recognition_at) : "Venter på første treff";
  $("#recognitions-body").innerHTML = data.items.length ? data.items.map(recognitionRow).join("") : '<tr class="empty-row"><td colspan="6">Ingen gjenkjenninger matcher filteret.</td></tr>';
  $("#recognition-guidance").hidden = Number(totals.total || 0) > 0;
}

function localDateValue(date = new Date()) {
  const parts = new Intl.DateTimeFormat("en-CA", { year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(date);
  const values = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  return `${values.year}-${values.month}-${values.day}`;
}

function shiftedDate(value, days) {
  const date = new Date(`${value}T12:00:00`);
  date.setDate(date.getDate() + days);
  return localDateValue(date);
}

function plateValidationBadge(item) {
  const validation = item.validation || {};
  if (item.is_likely_ocr_variant) {
    return `<span class="recognition-badge pending">Mulig variant</span><small>Foreslått: ${escapeHtml(item.likely_canonical_plate || "–")}</small>`;
  }
  if (validation.is_valid === true) {
    const label = validation.country || (validation.local_match ? "Lokalt bekreftet" : "Bekreftet");
    const detail = [validation.source, validation.vehicle_label].filter(Boolean).join(" · ") || validation.message || "";
    return `<span class="recognition-badge known">${escapeHtml(label)}</span><small>${escapeHtml(detail)}</small>`;
  }
  if (validation.likely_misread) {
    return `<span class="recognition-badge invalid">Sannsynlig feillesing</span><small>${escapeHtml(validation.message || "Ingen registertreff")}</small>`;
  }
  const label = validation.status === "error" ? "Oppslag utsatt" : "Valideres";
  return `<span class="recognition-badge pending">${label}</span><small>${escapeHtml(validation.error || validation.message || "Venter")}</small>`;
}

function plateRow(item) {
  const score = item.average_unifi_score === null || item.average_unifi_score === undefined
    ? "Uten score"
    : `${Number(item.average_unifi_score).toLocaleString("nb-NO", { maximumFractionDigits: 1 })}/100`;
  const cameras = (item.camera_names || []).map((name) => `<span class="tag">${escapeHtml(name)}</span>`).join("") || '<span class="tag muted">Ukjent</span>';
  return `<tr data-plate-row="${escapeHtml(item.plate)}" data-status="${escapeHtml(item.presentation_status || "pending_review")}">
    <td><strong class="plate-number">${escapeHtml(item.plate)}</strong><small>${item.known_in_protect ? "Kjent i UniFi Protect" : escapeHtml(item.display_value || "")}</small></td>
    <td><div class="plate-validation-cell">${plateValidationBadge(item)}</div></td>
    <td class="event-time"><strong>${dateTime(item.first_detected_at)}</strong><small>Sist ${dateTime(item.last_detected_at)}</small></td>
    <td><strong>${number(item.detection_count)}</strong><small>${item.ocr_variant_candidates?.length ? `${number(item.ocr_variant_candidates.length)} OCR-variant(er)` : "samme normaliserte skilt"}</small></td>
    <td><strong>${escapeHtml(score)}</strong><small>${number(item.scored_detection_count)} med score</small></td>
    <td><div class="tag-list">${cameras}</div></td>
    <td><div class="plate-actions"><button class="secondary-button plate-detail" data-plate="${escapeHtml(item.plate)}" type="button">Detaljer</button><button class="secondary-button plate-validate" data-plate="${escapeHtml(item.plate)}" type="button">Valider på nytt</button></div></td>
  </tr>`;
}

function renderPlateRows() {
  const items = state.plates?.items || [];
  const needle = ($("#plates-search").value || "").trim().toLocaleLowerCase("nb-NO");
  const status = $("#plates-status").value;
  const selected = items.filter((item) => {
    if (status && item.presentation_status !== status) return false;
    if (!needle) return true;
    const validation = item.validation || {};
    return [
      item.plate,
      item.display_value,
      validation.country,
      validation.source,
      validation.vehicle_label,
      ...(item.camera_names || []),
    ].filter(Boolean).join(" ").toLocaleLowerCase("nb-NO").includes(needle);
  });
  $("#plates-body").innerHTML = selected.length ? selected.map(plateRow).join("") : '<tr class="empty-row"><td colspan="7">Ingen skilt matcher dato og filter.</td></tr>';
}

async function loadPlates() {
  const dayInput = $("#plates-day");
  if (!dayInput.value) dayInput.value = localDateValue();
  const data = await api(`/api/license-plates/daily?day=${encodeURIComponent(dayInput.value)}`);
  state.plates = data;
  const summary = data.summary || {};
  $("#plates-unique").textContent = number(summary.unique_plates);
  $("#plates-detections").textContent = `${number(summary.detections)} deteksjoner`;
  $("#plates-valid").textContent = number(summary.validated_plates);
  $("#plates-pending").textContent = number(summary.pending_validation);
  $("#plates-misreads").textContent = number(summary.likely_misreads);
  $("#plates-last").textContent = data.items?.[0]?.last_detected_at ? dateTime(data.items[0].last_detected_at) : "Ingen treff";
  $("#plates-next").disabled = Boolean(data.is_today);
  renderPlateRows();
}

async function openPlate(plate) {
  const data = await api(`/api/license-plates/${encodeURIComponent(plate)}`);
  const validation = data.validation || {};
  $("#drawer-title").textContent = `Skilt ${data.plate}`;
  $("#drawer-snapshot").innerHTML = '<div class="snapshot-placeholder"><strong>Valideringsspor</strong><span>Råbilder og observasjoner ligger urørt i hendelsesloggen.</span></div>';
  $("#drawer-summary").innerHTML = [
    ["Status", validation.message || validation.status],
    ["Gyldig", validation.is_valid === true ? "Ja" : validation.is_valid === false ? "Nei" : "Uavklart"],
    ["Land", validation.country || "–"],
    ["Kilde", validation.source || "–"],
    ["Kjøretøy", validation.vehicle_label || "–"],
    ["Kontrollert", dateTime(validation.checked_at)],
  ].map(([label, value]) => `<div><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`).join("");
  $("#drawer-json").textContent = JSON.stringify(validation.sources || {}, null, 2);
  $("#event-drawer").hidden = false;
  $("#drawer-backdrop").hidden = false;
  document.body.style.overflow = "hidden";
}

async function validatePlate(button) {
  button.disabled = true;
  const original = button.textContent;
  button.textContent = "Kontrollerer …";
  try {
    const result = await api(`/api/license-plates/${encodeURIComponent(button.dataset.plate)}/validate`, { method: "POST", body: "{}" });
    toast(result.validation?.message || "Valideringen er oppdatert");
    await loadPlates();
  } catch (error) {
    toast(error.message, true);
  } finally {
    button.disabled = false;
    button.textContent = original;
  }
}

const bollardStatusLabels = {
  uncalibrated: "Ikke kalibrert",
  normal: "Normal",
  changed: "Ny forskjell",
  obscured: "Midlertidig skjult",
  suspected: "Mistenkt avvik",
  camera_error: "Kamerafeil",
};

function bollardStatusBadge(status) {
  const value = status || "uncalibrated";
  return `<span class="bollard-status ${escapeHtml(value)}">${escapeHtml(bollardStatusLabels[value] || value)}</span>`;
}

function bollardOverlay(region) {
  const roi = region.roi || {};
  if (Array.isArray(roi.polygon) && roi.polygon.length >= 3) {
    const points = roi.polygon.map((point) => `${Number(point.x || 0) * 100},${Number(point.y || 0) * 100}`).join(" ");
    const anchor = roi.polygon[0] || { x: 0, y: 0 };
    return `<svg class="bollard-polygon-overlay ${escapeHtml(region.status || "normal")}" viewBox="0 0 100 100" preserveAspectRatio="none" aria-label="${escapeHtml(region.display_name)}"><polygon points="${points}"></polygon><text x="${Number(anchor.x || 0) * 100}" y="${Math.max(3, Number(anchor.y || 0) * 100 - 1)}">${escapeHtml(region.display_name)}</text></svg>`;
  }
  const style = `left:${Number(roi.x || 0) * 100}%;top:${Number(roi.y || 0) * 100}%;width:${Number(roi.width || 0) * 100}%;height:${Number(roi.height || 0) * 100}%`;
  return `<span class="bollard-roi ${escapeHtml(region.status || "normal")}" style="${style}" title="${escapeHtml(region.display_name)}"><b>${escapeHtml(region.display_name)}</b></span>`;
}

function nextBollardName(cameraId) {
  const names = new Set((state.bollards?.regions || []).filter((row) => row.camera_id === cameraId).map((row) => String(row.display_name || "").trim().toLocaleLowerCase()));
  let index = 1;
  while (names.has(`pullert ${index}`)) index += 1;
  return `Pullert ${index}`;
}

function bollardCameraCard(camera) {
  if (!camera.camera_id) {
    return `<article class="bollard-camera-card missing"><div class="bollard-camera-heading"><div><strong>${escapeHtml(camera.name)}</strong><small>Ikke funnet i kamerakatalogen</small></div>${bollardStatusBadge("camera_error")}</div><div class="bollard-camera-missing">Kameraet må være tilkoblet UniFi Protect før det kan kalibreres.</div></article>`;
  }
  const regions = (state.bollards?.regions || []).filter((row) => row.camera_id === camera.camera_id);
  const connected = camera.state === "CONNECTED";
  const source = `/api/bollards/cameras/${encodeURIComponent(camera.camera_id)}/snapshot?v=${Date.now()}`;
  const suggestedName = nextBollardName(camera.camera_id);
  return `<article class="bollard-camera-card" data-camera-id="${escapeHtml(camera.camera_id)}">
    <div class="bollard-camera-heading"><div><strong>${escapeHtml(camera.name)}</strong><small>${connected ? "Tilkoblet" : escapeHtml(camera.state || "Ukjent status")} · ${number(regions.length)} markerte områder</small></div><span class="recognition-badge ${connected ? "known" : "invalid"}">${connected ? "På nett" : "Frakoblet"}</span></div>
    <div class="bollard-frame" data-camera-id="${escapeHtml(camera.camera_id)}">
      <img src="${source}" alt="Direktebilde fra ${escapeHtml(camera.name)}" draggable="false">
      <div class="bollard-roi-layer">${regions.map(bollardOverlay).join("")}<span class="bollard-selection" hidden></span></div>
      <span class="bollard-draw-hint">Dra en ramme rundt pullerten</span>
    </div>
    <div class="bollard-camera-controls">
      <label><span>Navn på fysisk pullert</span><input class="bollard-name-input" type="text" value="${escapeHtml(suggestedName)}" maxlength="120" aria-label="Navn på pullert"></label>
      <div class="bollard-camera-buttons"><button class="secondary-button bollard-refresh-camera" type="button">Nytt bilde</button><button class="primary-button bollard-start-draw" type="button" ${connected ? "" : "disabled"}>Marker med overlay</button></div>
    </div>
  </article>`;
}

function renderBollardCameras(data) {
  const byName = new Map((data.cameras || []).map((camera) => [camera.name, camera]));
  const byCamera = new Map((data.camera_monitors || []).map((monitor) => [monitor.camera_id, monitor]));
  const cameras = (data.target_camera_names || []).map((name) => byName.get(name) || { name, camera_id: null, state: "MISSING" });
  $("#bollard-comparison-grid").innerHTML = cameras.map((camera) => {
    const monitor = byCamera.get(camera.camera_id) || {};
    if (!camera.camera_id) return `<article class="bollard-comparison-card missing"><div class="bollard-camera-heading"><div><strong>${escapeHtml(camera.name)}</strong><small>Kameraet er ikke tilgjengelig</small></div>${bollardStatusBadge("camera_error")}</div></article>`;
    const version = Date.now();
    const baselineSource = monitor.baseline_crop_url || monitor.baseline_url;
    const latestSource = monitor.latest_crop_url || monitor.latest_url;
    const overlaySource = monitor.overlay_crop_url || monitor.overlay_url;
    const baseline = baselineSource ? `${baselineSource}?v=${version}` : `/api/bollards/cameras/${encodeURIComponent(camera.camera_id)}/snapshot?v=${version}`;
    const latest = latestSource ? `${latestSource}?v=${version}` : baseline;
    const overlay = overlaySource ? `${overlaySource}?v=${version}` : latest;
    const difference = monitor.changed_fraction == null ? "Ikke sammenlignet ennå" : `${(Number(monitor.changed_fraction) * 100).toFixed(2)} % lokal forskjell`;
    const checked = monitor.last_checked_at ? `Sist sammenlignet ${dateTime(monitor.last_checked_at)}` : "Venter på første femminuttersbilde";
    const baselineLabel = monitor.baseline_captured_at ? `Referanse · ${dateTime(monitor.baseline_captured_at)}` : "Referanse";
    const latestLabel = monitor.latest_captured_at ? `Siste · ${dateTime(monitor.latest_captured_at)}` : "Siste bilde";
    const baselineStamp = monitor.baseline_captured_at ? dateTime(monitor.baseline_captured_at) : "Ikke tilgjengelig";
    const latestStamp = monitor.latest_captured_at ? dateTime(monitor.latest_captured_at) : "Ikke tilgjengelig";
    const displayCrop = monitor.display_crop || {};
    const cropAspect = Number(displayCrop.width) > 0 && Number(displayCrop.height) > 0
      ? Number(displayCrop.width) / Number(displayCrop.height)
      : 16 / 9;
    return `<article class="bollard-comparison-card" data-camera-id="${escapeHtml(camera.camera_id)}">
      <div class="bollard-camera-heading"><div><strong>${escapeHtml(camera.name)}</strong><small>${escapeHtml(checked)}</small></div>${bollardStatusBadge(monitor.status || "uncalibrated")}</div>
      <div class="bollard-overlay-stage" style="aspect-ratio:${cropAspect.toFixed(6)}">
        <img class="bollard-reference-image" src="${escapeHtml(baseline)}" alt="Referanse fra ${escapeHtml(camera.name)}">
        <img class="bollard-current-image" src="${escapeHtml(latest)}" alt="Nytt bilde fra ${escapeHtml(camera.name)}" style="opacity:.5">
        <img class="bollard-difference-image" src="${escapeHtml(overlay)}" alt="Beregnet forskjell fra ${escapeHtml(camera.name)}" hidden>
        <span class="bollard-image-label reference">${escapeHtml(baselineLabel)}</span><span class="bollard-image-label current">${escapeHtml(latestLabel)}</span>
      </div>
      <div class="bollard-comparison-controls">
        <label class="bollard-opacity-control">
          <span class="bollard-opacity-endpoint is-reference"><b>Referanse</b><small>${escapeHtml(baselineStamp)}</small></span>
          <span class="bollard-opacity-endpoint is-latest"><b>Siste bilde <em class="bollard-opacity-value">50 %</em></b><small>${escapeHtml(latestStamp)}</small></span>
          <input class="bollard-opacity" type="range" min="0" max="100" value="50" aria-label="Gjennomsiktighet for siste bilde" ${monitor.latest_url ? "" : "disabled"}>
        </label>
        <div class="bollard-camera-buttons"><button class="secondary-button bollard-toggle-difference" type="button" ${monitor.overlay_url ? "" : "disabled"}>Vis røde forskjeller</button><button class="secondary-button bollard-scene-baseline" type="button">Erstatt referanse</button></div>
        <div class="bollard-comparison-meta"><span>${escapeHtml(difference)}</span><span>${monitor.latest_captured_at ? `Nytt bilde ${dateTime(monitor.latest_captured_at)}` : "Ingen nytt bilde ennå"}</span></div>
      </div>
    </article>`;
  }).join("");
}

function bollardRegionRow(region) {
  const score = region.last_match_score == null ? "Ikke analysert" : `${Math.round(Number(region.last_match_score) * 100)} % treff`;
  const offset = region.last_offset_x == null ? "–" : `${region.last_offset_x >= 0 ? "+" : ""}${region.last_offset_x}, ${region.last_offset_y >= 0 ? "+" : ""}${region.last_offset_y} px`;
  return `<tr>
    <td><strong>${escapeHtml(region.display_name)}</strong><small>${escapeHtml(region.bollard_key)}</small></td>
    <td>${escapeHtml(region.camera_name || region.camera_id)}</td>
    <td>${bollardStatusBadge(region.status)}${region.last_error ? `<small>${escapeHtml(region.last_error)}</small>` : ""}</td>
    <td>${region.last_checked_at ? dateTime(region.last_checked_at) : "Ikke kontrollert"}</td>
    <td><strong>${escapeHtml(score)}</strong><small>${escapeHtml(offset)}</small></td>
    <td><div class="bollard-row-actions"><a class="secondary-button button-link" href="${escapeHtml(region.baseline_url)}" target="_blank" rel="noreferrer">Referanse</a><button class="secondary-button bollard-recalibrate" data-region-id="${region.region_id}" type="button">Ny overlay</button><button class="secondary-button bollard-refresh-baseline" data-region-id="${region.region_id}" type="button">Nytt bilde</button><button class="danger-button bollard-delete-region" data-region-id="${region.region_id}" type="button">Slett</button></div></td>
  </tr>`;
}

function bollardIncidentCard(incident) {
  const evidence = Object.entries(incident.evidence || {});
  const context = incident.context || {};
  const plates = (context.plates || []).map((row) => row.normalized_value).filter(Boolean);
  return `<article class="bollard-incident ${escapeHtml(incident.status)}">
    <div class="bollard-incident-heading"><div><span class="bollard-status ${escapeHtml(incident.status)}">${escapeHtml(incident.status === "active" ? "Aktiv alarm" : incident.status === "acknowledged" ? "Kvittert" : "Avsluttet")}</span><h4>${escapeHtml(incident.display_name)}</h4><p>Bekreftet ${dateTime(incident.confirmed_at || incident.detected_at)}${plates.length ? ` · Skilt i nærheten: ${escapeHtml([...new Set(plates)].join(", "))}` : ""}</p></div>${incident.status === "active" ? `<button class="secondary-button bollard-acknowledge" data-incident-id="${incident.incident_id}" type="button">Kvitter</button>` : ""}</div>
    <div class="bollard-evidence-grid">${evidence.map(([cameraId, item]) => `<figure><figcaption>${escapeHtml(item.camera_name || cameraId)} · ${escapeHtml(item.state || "avvik")}</figcaption><div><a href="${escapeHtml(item.before_url)}" target="_blank" rel="noreferrer"><img src="${escapeHtml(item.before_url)}" alt="Godkjent referanse"></a><a href="${escapeHtml(item.after_url)}" target="_blank" rel="noreferrer"><img src="${escapeHtml(item.after_url)}" alt="Bilde ved avvik"></a></div><small>Referanse → avvik · ${Math.round(Number(item.score || 0) * 100)} % treff · ${number(item.distance_pixels)} px</small></figure>`).join("")}</div>
  </article>`;
}

async function loadBollards() {
  const data = await api("/api/bollards");
  state.bollards = data;
  const summary = data.summary || {};
  const settings = data.settings || {};
  const runtime = data.runtime || {};
  $("#bollard-cameras").textContent = `${number(summary.connected_cameras)} / ${number(summary.target_cameras)}`;
  $("#bollard-regions").textContent = `${number(summary.baseline_cameras || 0)} / 3`;
  $("#bollard-keys").textContent = "faste helbilder";
  $("#bollard-active").textContent = number(summary.active_incidents);
  $("#bollard-last-check").textContent = runtime.last_success_at ? `Sist kontrollert ${dateTime(runtime.last_success_at)}` : "Ingen analyse utført";
  $("#bollard-notify").textContent = settings.notification_enabled ? (runtime.notification_configured ? "Aktiv" : "Mangler kanal") : "Av";
  $("#bollard-monitor-state").textContent = settings.monitoring_enabled ? "Sammenligning aktiv" : "Ikke aktivert";
  $("#bollard-monitor-copy").textContent = settings.monitoring_enabled ? "Nytt bilde fra alle tre kameraer hvert 5. minutt" : "Tre faste referansebilder beholdes til du erstatter dem";
  $("#bollard-monitoring-enabled").value = String(Boolean(settings.monitoring_enabled));
  $("#bollard-interval").value = 300;
  $("#bollard-confirmation").value = 300;
  $("#bollard-notification-enabled").value = String(settings.notification_enabled !== false);
  renderBollardCameras(data);
  $("#bollard-incidents").innerHTML = data.incidents?.length ? data.incidents.map(bollardIncidentCard).join("") : '<div class="bollard-empty"><strong>Ingen registrerte avvik</strong><p>Når overvåkingen er aktiv, lagres referanse og kontrollbilde her ved en bekreftet hendelse.</p></div>';
}

function refreshBollardCamera(button) {
  const card = button.closest(".bollard-camera-card");
  const image = $(".bollard-frame img", card);
  image.src = `/api/bollards/cameras/${encodeURIComponent(card.dataset.cameraId)}/snapshot?v=${Date.now()}`;
}

function startBollardDrawing(button) {
  const card = button.closest(".bollard-camera-card");
  const name = $(".bollard-name-input", card).value.trim();
  if (!name) { toast("Gi pullerten et navn før du markerer området", true); return; }
  openBollardCalibrator(card.dataset.cameraId, name);
}

function bollardPointerPoint(event, frame) {
  const rect = frame.getBoundingClientRect();
  return {
    x: Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width)),
    y: Math.max(0, Math.min(1, (event.clientY - rect.top) / rect.height)),
  };
}

function polygonArea(points) {
  if (points.length < 3) return 0;
  let sum = 0;
  points.forEach((point, index) => {
    const next = points[(index + 1) % points.length];
    sum += point.x * next.y - next.x * point.y;
  });
  return Math.abs(sum) / 2;
}

function setBollardCalibrationZoom(zoom) {
  const value = Math.max(1, Math.min(2, Number(zoom) || 1));
  $("#bollard-calibrator-canvas").style.width = `${value * 100}%`;
  document.querySelectorAll("[data-bollard-zoom]").forEach((button) => button.classList.toggle("active", Number(button.dataset.bollardZoom) === value));
}

function renderBollardPolygon() {
  const drawing = state.bollardDrawing;
  if (!drawing?.polygonMode) return;
  const points = drawing.points || [];
  const svg = $(".bollard-polygon-layer", drawing.frame);
  const pointText = points.map((point) => `${(point.x * 100).toFixed(3)},${(point.y * 100).toFixed(3)}`).join(" ");
  svg.innerHTML = `${points.length >= 3 ? `<polygon class="bollard-polygon-fill" points="${pointText}"></polygon>` : ""}<polyline class="bollard-polygon-line" points="${pointText}"></polyline>${points.map((point) => `<circle class="bollard-polygon-point" cx="${point.x * 100}" cy="${point.y * 100}" r="0.65"></circle>`).join("")}`;
  $("#bollard-calibrator-undo").disabled = points.length === 0;
  const save = $("#bollard-calibrator-save");
  const feedback = $("#bollard-calibrator-feedback");
  const preview = $("#bollard-crop-preview");
  feedback.className = "bollard-calibrator-feedback";
  drawing.roi = null;
  save.disabled = true;
  if (points.length < 3) {
    feedback.textContent = `${number(points.length)} punkt${points.length === 1 ? "" : "er"} valgt. Fortsett rundt ytterkanten.`;
    preview.innerHTML = "<span>Formen vises her når du markerer</span>";
    return;
  }
  const x = Math.min(...points.map((point) => point.x));
  const y = Math.min(...points.map((point) => point.y));
  const right = Math.max(...points.map((point) => point.x));
  const bottom = Math.max(...points.map((point) => point.y));
  const width = right - x;
  const height = bottom - y;
  const image = $("img", drawing.frame);
  const naturalWidth = image?.naturalWidth || 3840;
  const naturalHeight = image?.naturalHeight || 2160;
  const pixelWidth = Math.round(width * naturalWidth);
  const pixelHeight = Math.round(height * naturalHeight);
  const area = polygonArea(points);
  const valid = points.length >= 6 && pixelWidth >= 55 && pixelHeight >= 90 && area >= 0.00004;
  drawing.roi = { x, y, width, height, polygon: points.map((point) => ({ x: point.x, y: point.y })) };
  const paddingX = Math.max(4, pixelWidth * 0.08);
  const paddingY = Math.max(4, pixelHeight * 0.08);
  const viewX = Math.max(0, x * naturalWidth - paddingX);
  const viewY = Math.max(0, y * naturalHeight - paddingY);
  const viewWidth = Math.min(naturalWidth - viewX, pixelWidth + paddingX * 2);
  const viewHeight = Math.min(naturalHeight - viewY, pixelHeight + paddingY * 2);
  const naturalPoints = points.map((point) => `${point.x * naturalWidth},${point.y * naturalHeight}`).join(" ");
  preview.innerHTML = `<svg viewBox="${viewX} ${viewY} ${viewWidth} ${viewHeight}" preserveAspectRatio="xMidYMid meet"><image href="${escapeHtml(drawing.source)}" x="0" y="0" width="${naturalWidth}" height="${naturalHeight}" preserveAspectRatio="none"></image><polygon points="${naturalPoints}" fill="rgba(44,214,145,.38)" stroke="#1ed58c" stroke-width="${Math.max(2, naturalWidth / 900)}"></polygon></svg>`;
  if (valid) {
    feedback.classList.add("ready");
    feedback.textContent = `${number(points.length)} punkter · ${number(pixelWidth)} × ${number(pixelHeight)} px. Overlayen er klar til lagring.`;
    save.disabled = false;
  } else {
    feedback.classList.add("warning");
    feedback.textContent = points.length < 6 ? `Bruk minst 6 punkter. Du har valgt ${number(points.length)}.` : `Formen er for liten (${number(pixelWidth)} × ${number(pixelHeight)} px). Ta med hele pullerten fra topp til fotplate.`;
  }
}

function openBollardCalibrator(cameraId, name, region = null) {
  const camera = (state.bollards?.cameras || []).find((item) => item.camera_id === cameraId);
  if (!camera) { toast("Kameraet ble ikke funnet", true); return; }
  const source = `/api/bollards/cameras/${encodeURIComponent(cameraId)}/snapshot?v=${Date.now()}`;
  const regions = (state.bollards?.regions || []).filter((item) => item.camera_id === cameraId);
  const frame = $("#bollard-calibrator-frame");
  frame.innerHTML = `<img src="${source}" alt="Stort kalibreringsbilde fra ${escapeHtml(camera.name)}" draggable="false"><div class="bollard-roi-layer">${regions.map(bollardOverlay).join("")}</div><svg class="bollard-polygon-layer" viewBox="0 0 100 100" preserveAspectRatio="none" aria-label="Ny overlay"></svg>`;
  frame.classList.add("drawing");
  const existingPoints = Array.isArray(region?.roi?.polygon) ? region.roi.polygon.map((point) => ({ x: Number(point.x), y: Number(point.y) })) : [];
  state.bollardDrawing = { frame, cameraId, name, source, points: existingPoints, polygonMode: true, roi: null };
  $("#bollard-calibrator-title").textContent = region ? `Ny overlay for ${name}` : `Marker hele ${name}`;
  $("#bollard-calibrator-camera").textContent = camera.name;
  $("#bollard-calibrator-name").value = name;
  const names = [...new Set((state.bollards?.regions || []).map((item) => item.display_name).filter(Boolean))];
  $("#bollard-name-options").innerHTML = names.map((value) => `<option value="${escapeHtml(value)}"></option>`).join("");
  $("#bollard-calibrator").hidden = false;
  document.body.classList.add("modal-open");
  setBollardCalibrationZoom(1);
  renderBollardPolygon();
  $("img", frame).addEventListener("load", renderBollardPolygon, { once: true });
}

function closeBollardCalibrator() {
  $("#bollard-calibrator").hidden = true;
  document.body.classList.remove("modal-open");
  state.bollardDrawing = null;
}

function resetBollardPolygon() {
  if (!state.bollardDrawing?.polygonMode) return;
  state.bollardDrawing.points = [];
  renderBollardPolygon();
}

async function saveBollardCalibration() {
  const drawing = state.bollardDrawing;
  const name = $("#bollard-calibrator-name").value.trim();
  if (!drawing?.polygonMode || !drawing.roi || !name) { toast("Fullfør overlayen og velg navn", true); return; }
  const button = $("#bollard-calibrator-save");
  button.disabled = true;
  button.textContent = "Lagrer …";
  try {
    await api("/api/bollards/regions", { method: "POST", body: JSON.stringify({ display_name: name, bollard_key: name, camera_id: drawing.cameraId, roi: drawing.roi }) });
    closeBollardCalibrator();
    await loadBollards();
    const result = await api("/api/bollards/analyze-now", { method: "POST", body: "{}" });
    const row = (result.results || []).find((item) => item.camera_id === drawing.cameraId && item.display_name === name);
    toast(row?.state === "normal" ? `${name} er lagret og kontrollert som normal` : `${name} er lagret. Kontroller status før aktivering.`, row && row.state !== "normal");
    await loadBollards();
  } catch (error) {
    toast(error.message, true);
  } finally {
    button.textContent = "Lagre overlay";
    if (!$("#bollard-calibrator").hidden) renderBollardPolygon();
  }
}

async function saveBollardSettings() {
  const button = $("#bollard-save-settings");
  button.disabled = true;
  try {
    await api("/api/bollards/settings", { method: "POST", body: JSON.stringify({
      monitoring_enabled: $("#bollard-monitoring-enabled").value === "true",
      analysis_interval_seconds: 300,
      confirmation_seconds: 300,
      notification_enabled: $("#bollard-notification-enabled").value === "true",
    }) });
    toast("Femminutters-sammenligningen er oppdatert");
    await loadBollards();
  } catch (error) { toast(error.message, true); }
  finally { button.disabled = false; }
}

async function analyzeBollards() {
  const button = $("#bollard-analyze");
  button.disabled = true;
  try {
    const result = await api("/api/bollards/analyze-now", { method: "POST", body: "{}" });
    toast(`${number(result.checked)} kameraer sammenlignet · ${number(result.new_incidents)} nye avvik`);
    await loadBollards();
  } catch (error) { toast(error.message, true); }
  finally { button.disabled = false; }
}

async function loadIntegrationStatus() {
  const data = await api("/api/integration-status");
  state.integrationStatus = data;
  const health = state.overview?.health || {};
  const nvrOnline = Boolean(health.websocket_connected);
  $("#integration-nvr-dot").classList.toggle("online", nvrOnline);
  $("#integration-nvr-dot").classList.toggle("offline", !nvrOnline);
  $("#integration-nvr").textContent = `${data.nvr_host || "lokal gateway"} · ${nvrOnline ? "WebSocket tilkoblet" : "kobler opp igjen"}`;
  $("#integration-api-dot").classList.toggle("online", data.read_api_token_configured);
  $("#integration-api-dot").classList.toggle("offline", !data.read_api_token_configured);
  $("#integration-api").textContent = data.read_api_token_configured ? "Beskyttet token er konfigurert" : "Mangler lesetoken";
  const alarm = data.alarm_manager || {};
  const webhookCount = Number(alarm.webhooks?.total || 0);
  const webhookReady = Boolean(data.webhook_token_configured || data.webhook_allowed_ips?.length);
  const webhookDot = $("#integration-webhook-dot");
  webhookDot.classList.toggle("online", webhookCount > 0);
  webhookDot.classList.toggle("pending", webhookReady && webhookCount === 0);
  webhookDot.classList.toggle("offline", !webhookReady);
  $("#integration-webhook").textContent = webhookCount > 0
    ? `${number(webhookCount)} lokale kall · sist ${dateTime(alarm.webhooks?.last_received_at)}`
    : webhookReady ? "Klar – venter på første lokale POST-kall" : "Mangler webhook-autentisering";
  $("#integration-endpoints").innerHTML = Object.entries(data.endpoints || {}).filter(([key]) => key !== "alarm_webhook").map(([key, path]) => `<div><code>${escapeHtml(path)}</code><small>${escapeHtml({ status: "Drift og kø", build: "Gjeldende PL-build", build_log: "Komplett buildhistorikk", cameras: "Kamerakatalog", capabilities: "Alle deteksjonsmuligheter", stats: "Samlede nøkkeltall", events: "Hendelser med markør", recognitions: "Skilt og personer", stream: "SSE sanntidsstrøm" }[key] || key)}</small></div>`).join("");
  $("#webhook-url").textContent = `${location.origin}${data.endpoints?.alarm_webhook || "/api/v1/webhooks/unifi-alarm"}`;
  const verified = Number(alarm.verified_rule_count || 0);
  const required = Number(alarm.required_rule_count || 4);
  $("#alarm-progress-title").textContent = `${number(verified)} av ${number(required)} signaler verifisert`;
  $("#alarm-progress-copy").textContent = alarm.all_rules_verified ? "Alle fire webhook-variantene er mottatt og lagret." : "Gule signaler blir grønne når Protect sender et reelt treff.";
  $("#alarm-progress-badge").textContent = alarm.all_rules_verified ? "Fullført" : "Venter";
  $("#alarm-readiness").classList.toggle("ready", Boolean(alarm.all_rules_verified));
  $("#alarm-rule-list").innerHTML = (alarm.required_rules || []).map((rule) => `<div class="alarm-rule ${rule.verified ? "verified" : ""}">${escapeHtml(rule.label)}<span>${rule.verified ? `${number(rule.received_count)} mottatt` : "ikke testet"}</span></div>`).join("");
}

async function updateRule(button) {
  const enabled = button.getAttribute("aria-checked") !== "true";
  button.disabled = true;
  try {
    await api(`/api/config/${encodeURIComponent(button.dataset.kind)}/${encodeURIComponent(button.dataset.key)}`, { method: "PATCH", body: JSON.stringify({ store_enabled: enabled }) });
    button.setAttribute("aria-checked", String(enabled));
    toast(enabled ? "Lagring aktivert" : "Lagring deaktivert");
    await loadCatalog();
  } catch (error) { toast(error.message, true); }
  finally { button.disabled = false; }
}

async function saveSettings() {
  const button = $("#save-settings");
  button.disabled = true;
  try {
    await api("/api/config/settings", { method: "PATCH", body: JSON.stringify({
      default_store_new_event_types: $("#setting-default-store").value === "true",
      retention_days: Number($("#setting-retention-days").value),
      catalog_sample_limit_bytes: Number($("#setting-sample-limit").value),
      snapshots_enabled: $("#setting-snapshots-enabled").value === "true",
      snapshot_high_quality: $("#setting-snapshot-quality").value === "true",
      snapshot_max_bytes: Number($("#setting-snapshot-max").value),
    }) });
    toast("Innstillingene er lagret");
    await loadCatalog();
  } catch (error) { toast(error.message, true); }
  finally { button.disabled = false; }
}

async function loadEvents(reset = false) {
  if (reset) state.eventOffset = 0;
  const params = new URLSearchParams({
    q: $("#filter-query").value,
    hours: $("#filter-hours").value,
    event_type: $("#filter-event-type").value,
    detection_type: $("#filter-detection-type").value,
    camera_id: $("#filter-camera").value,
    limit: state.pageSize,
    offset: state.eventOffset,
  });
  const data = await api(`/api/events?${params}`);
  state.events = data;
  $("#events-total").textContent = number(data.total);
  $("#events-body").innerHTML = data.rows.length ? data.rows.map((row) => eventRow(row, true)).join("") : '<tr class="empty-row"><td colspan="8">Ingen hendelser matcher filteret.</td></tr>';
  const page = Math.floor(state.eventOffset / state.pageSize) + 1;
  const pages = Math.max(1, Math.ceil(data.total / state.pageSize));
  $("#events-page-label").textContent = `Side ${page} av ${pages}`;
  $("#events-prev").disabled = state.eventOffset === 0;
  $("#events-next").disabled = state.eventOffset + state.pageSize >= data.total;
}

async function openEvent(eventId) {
  try {
    const row = await api(`/api/events/${encodeURIComponent(eventId)}`);
    $("#drawer-title").textContent = "Hendelsesdetaljer";
    let raw = row.raw;
    if (typeof raw === "string") { try { raw = JSON.parse(raw); } catch (_) {} }
    const snapshot = $("#drawer-snapshot");
    if (row.snapshot_status === "stored") {
      snapshot.innerHTML = `<img src="/api/events/${encodeURIComponent(row.source_event_id)}/snapshot" alt="Stillbilde fra ${escapeHtml(row.camera_name || row.camera_id || "kamera")}">`;
    } else {
      const snapshotMessage = row.snapshot_status === "failed" ? `Stillbildet kunne ikke lagres${row.snapshot_error ? `: ${row.snapshot_error}` : "."}` : "Stillbilde er ikke tilgjengelig for denne hendelsen.";
      snapshot.innerHTML = `<div class="snapshot-placeholder"><strong>Ingen stillbilde</strong><span>${escapeHtml(snapshotMessage)}</span></div>`;
    }
    $("#drawer-summary").innerHTML = [
      ["Kamera", row.camera_name || row.camera_id || "Ukjent"],
      ["Hendelse", row.event_type || "Ukjent"],
      ["Start", dateTime(row.start_at)],
      ["Varighet", duration(row.duration_ms)],
    ].map(([label, value]) => `<div><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`).join("");
    $("#drawer-json").textContent = typeof raw === "string" ? raw : JSON.stringify(raw, null, 2);
    $("#event-drawer").hidden = false;
    $("#drawer-backdrop").hidden = false;
    document.body.style.overflow = "hidden";
    $("#drawer-close").focus();
  } catch (error) { toast(error.message, true); }
}

async function openRecognition(recognitionId) {
  try {
    const row = await api(`/api/recognitions/${encodeURIComponent(recognitionId)}`);
    $("#drawer-title").textContent = "Gjenkjenningsdetaljer";
    const snapshot = $("#drawer-snapshot");
    if (row.snapshot_status === "stored") {
      snapshot.innerHTML = `<img src="/api/recognitions/${encodeURIComponent(row.recognition_id)}/snapshot" alt="Deteksjonsbilde fra ${escapeHtml(row.camera_name || row.camera_id || "kamera")}">`;
    } else {
      const message = row.snapshot_status === "pending" || row.snapshot_status === "capturing" ? "Bildet hentes fra kameraet nå." : "Denne eldre registreringen har ikke et sikkert deteksjonsbilde.";
      snapshot.innerHTML = `<div class="snapshot-placeholder"><strong>Ingen sikkert bilde</strong><span>${escapeHtml(message)}</span></div>`;
    }
    const known = row.is_known === true ? "Kjent" : row.is_known === false ? "Ukjent" : "Uavklart";
    $("#drawer-summary").innerHTML = [
      ["Type", recognitionKind(row.kind)],
      ["Verdi", row.value || "Ikke sendt av Protect"],
      ["Status", known],
      ["Kamera", row.camera_name || row.camera_id || "Ukjent"],
      ["Tidspunkt", dateTime(row.occurred_at)],
      ["Bildekamera", row.snapshot_camera_id || "Ikke lagret"],
      ["Bildetid", row.snapshot_captured_at ? dateTime(row.snapshot_captured_at) : "Ikke lagret"],
      ["Tidsavvik", row.snapshot_time_offset_ms == null ? "Ukjent" : `${row.snapshot_time_offset_ms >= 0 ? "+" : ""}${(Number(row.snapshot_time_offset_ms) / 1000).toFixed(2)} s`],
      ["Kobling", row.correlation_status || "unmatched"],
    ].map(([label, value]) => `<div><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`).join("");
    $("#drawer-json").textContent = JSON.stringify({ trigger: row.trigger_raw, webhook: row.webhook_raw }, null, 2);
    $("#event-drawer").hidden = false;
    $("#drawer-backdrop").hidden = false;
    document.body.style.overflow = "hidden";
    $("#drawer-close").focus();
  } catch (error) { toast(error.message, true); }
}

function closeDrawer() {
  $("#event-drawer").hidden = true;
  $("#drawer-backdrop").hidden = true;
  document.body.style.overflow = "";
}

async function loadStorage() {
  const data = await api("/api/storage");
  state.storage = data;
  const sizes = data.sizes || {};
  const rawBytes = (data.distribution || []).reduce((sum, row) => sum + Number(row.raw_bytes || 0), 0);
  $("#storage-total").textContent = bytes(sizes.ledger_total_bytes || sizes.events_total_bytes);
  $("#storage-ledger-counts").textContent = `${number(sizes.event_count)} hendelser · ${number(sizes.recognition_count)} gjenkjenninger · ${number(sizes.webhook_count)} webhooks`;
  $("#storage-snapshots").textContent = bytes(sizes.snapshot_bytes);
  $("#storage-snapshot-count").textContent = `${number(sizes.snapshot_count)} JPEG · ${number(sizes.snapshot_failures)} feil · ${bytes(rawBytes)} rå JSON`;
  $("#storage-indexes").textContent = bytes(sizes.ledger_index_bytes || sizes.events_index_bytes);
  $("#storage-retention").textContent = `${number(data.settings?.retention_days || 365)} dager`;
  renderStorageList("#storage-by-type", data.distribution || [], "event_type");
  renderStorageList("#storage-by-camera", data.cameras || [], "camera_name");
  $("#history-body").innerHTML = data.history?.length ? data.history.map((row) => `<tr><td>${dateTime(row.changed_at)}</td><td>${escapeHtml(row.target_kind)}</td><td>${escapeHtml(row.target_key)}</td><td class="history-change">${escapeHtml(typeof row.new_value === "string" ? row.new_value : JSON.stringify(row.new_value))}</td></tr>`).join("") : '<tr class="empty-row"><td colspan="4">Ingen endringer registrert ennå.</td></tr>';
}

function renderStorageList(selector, rows, labelKey) {
  const max = Math.max(1, ...rows.map((row) => Number(row.event_count || 0)));
  $(selector).innerHTML = rows.length ? rows.map((row) => `<div class="storage-row"><div><strong>${escapeHtml(row[labelKey] || "Ukjent")}</strong><small>${number(row.event_count)} hendelser · ${bytes(row.raw_bytes)}</small><div class="storage-bar"><span style="width:${(Number(row.event_count || 0) / max) * 100}%"></span></div></div><span class="summary-count">${number(row.event_count)}</span></div>`).join("") : '<p class="quiet-label">Ingen lagrede data ennå.</p>';
}

async function runRetention() {
  if (!confirm("Kjør oppbevaringsregelen nå? Hendelser eldre enn valgt antall dager slettes permanent.")) return;
  const button = $("#run-retention");
  button.disabled = true;
  try {
    const result = await api("/api/maintenance/retention", { method: "POST", body: "{}" });
    toast(`${number(result.deleted)} hendelser, ${number(result.deleted_recognitions)} gjenkjenninger, ${number(result.deleted_webhooks)} webhooks og ${number(result.deleted_snapshots)} bilder ble slettet`);
    await loadStorage();
  } catch (error) { toast(error.message, true); }
  finally { button.disabled = false; }
}

async function refreshPage() {
  const page = currentPage();
  const button = $("#refresh-button");
  button.disabled = true;
  try {
    if (!state.catalog) await loadCatalog();
    if (page === "dashboard") await loadOverview();
    if (page === "events") await loadEvents();
    if (page === "recognitions") await loadRecognitions();
    if (page === "plates") await loadPlates();
    if (page === "bollards") await loadBollards();
    if (page === "configuration") await loadCatalog();
    if (page === "storage") await loadStorage();
    if (page === "integrations") await loadIntegrationStatus();
    if (page === "builds") await loadBuilds();
  } catch (error) { toast(error.message, true); }
  finally { button.disabled = false; }
}

document.addEventListener("click", (event) => {
  const toggleButton = event.target.closest(".rule-toggle");
  if (toggleButton) updateRule(toggleButton);
  const detailButton = event.target.closest(".event-detail");
  if (detailButton) openEvent(detailButton.dataset.eventId);
  const recognitionButton = event.target.closest(".recognition-detail");
  if (recognitionButton) openRecognition(recognitionButton.dataset.recognitionId);
  const plateDetail = event.target.closest(".plate-detail");
  if (plateDetail) openPlate(plateDetail.dataset.plate).catch((error) => toast(error.message, true));
  const plateValidate = event.target.closest(".plate-validate");
  if (plateValidate) validatePlate(plateValidate);
  const bollardRefresh = event.target.closest(".bollard-refresh-camera");
  if (bollardRefresh) refreshBollardCamera(bollardRefresh);
  const bollardDraw = event.target.closest(".bollard-start-draw");
  if (bollardDraw) startBollardDrawing(bollardDraw);
  const sceneBaseline = event.target.closest(".bollard-scene-baseline");
  if (sceneBaseline && confirm("Erstatte det faste referansebildet for dette kameraet med et nytt nåbilde?")) {
    const card = sceneBaseline.closest(".bollard-comparison-card");
    sceneBaseline.disabled = true;
    api(`/api/bollards/cameras/${encodeURIComponent(card.dataset.cameraId)}/baseline`, { method: "POST", body: "{}" })
      .then(() => { toast("Nytt referansebilde er lagret"); return loadBollards(); })
      .catch((error) => toast(error.message, true))
      .finally(() => { sceneBaseline.disabled = false; });
  }
  const toggleDifference = event.target.closest(".bollard-toggle-difference");
  if (toggleDifference) {
    const card = toggleDifference.closest(".bollard-comparison-card");
    const differenceImage = $(".bollard-difference-image", card);
    const currentImage = $(".bollard-current-image", card);
    const stage = $(".bollard-overlay-stage", card);
    const showing = differenceImage.hidden;
    differenceImage.hidden = !showing;
    currentImage.hidden = showing;
    stage.classList.toggle("showing-difference", showing);
    toggleDifference.textContent = showing ? "Vis transparent overlegg" : "Vis røde forskjeller";
  }
  const recalibrate = event.target.closest(".bollard-recalibrate");
  if (recalibrate) {
    const region = (state.bollards?.regions || []).find((item) => String(item.region_id) === String(recalibrate.dataset.regionId));
    if (region) openBollardCalibrator(region.camera_id, region.display_name, region);
  }
  const zoom = event.target.closest("[data-bollard-zoom]");
  if (zoom) setBollardCalibrationZoom(zoom.dataset.bollardZoom);
  const baseline = event.target.closest(".bollard-refresh-baseline");
  if (baseline && confirm("Bruk et nytt kamerabilde som godkjent referanse? Gjør dette bare når pullerten står riktig.")) {
    api(`/api/bollards/regions/${baseline.dataset.regionId}/baseline`, { method: "POST", body: "{}" }).then(() => { toast("Ny referanse er lagret"); return loadBollards(); }).catch((error) => toast(error.message, true));
  }
  const removeRegion = event.target.closest(".bollard-delete-region");
  if (removeRegion && confirm("Slette dette kalibrerte området?")) {
    api(`/api/bollards/regions/${removeRegion.dataset.regionId}`, { method: "DELETE" }).then(() => { toast("Området er slettet"); return loadBollards(); }).catch((error) => toast(error.message, true));
  }
  const acknowledge = event.target.closest(".bollard-acknowledge");
  if (acknowledge) {
    api(`/api/bollards/incidents/${acknowledge.dataset.incidentId}/acknowledge`, { method: "POST", body: "{}" }).then(() => { toast("Avviket er kvittert"); return loadBollards(); }).catch((error) => toast(error.message, true));
  }
});
document.addEventListener("input", (event) => {
  const opacity = event.target.closest(".bollard-opacity");
  if (!opacity) return;
  const card = opacity.closest(".bollard-comparison-card");
  const currentImage = card?.querySelector(".bollard-current-image");
  const valueLabel = card?.querySelector(".bollard-opacity-value");
  if (currentImage) currentImage.style.opacity = String(Number(opacity.value) / 100);
  if (valueLabel) valueLabel.textContent = `${Number(opacity.value)} %`;
});
document.addEventListener("pointerdown", (event) => {
  const drawing = state.bollardDrawing;
  const frame = event.target.closest(".bollard-calibrator-frame.drawing");
  if (!frame || drawing?.frame !== frame || !drawing.polygonMode) return;
  event.preventDefault();
  if (drawing.points.length >= 80) { toast("Maksimalt 80 punkter per overlay", true); return; }
  drawing.points.push(bollardPointerPoint(event, frame));
  renderBollardPolygon();
});
$("#save-settings").addEventListener("click", saveSettings);
$("#events-filter-form").addEventListener("submit", (event) => { event.preventDefault(); loadEvents(true).catch((error) => toast(error.message, true)); });
$("#recognition-filter-form").addEventListener("submit", (event) => { event.preventDefault(); loadRecognitions().catch((error) => toast(error.message, true)); });
$("#plates-day").addEventListener("change", () => loadPlates().catch((error) => toast(error.message, true)));
$("#plates-search").addEventListener("input", renderPlateRows);
$("#plates-status").addEventListener("change", renderPlateRows);
$("#plates-previous").addEventListener("click", () => { $("#plates-day").value = shiftedDate($("#plates-day").value || localDateValue(), -1); loadPlates().catch((error) => toast(error.message, true)); });
$("#plates-next").addEventListener("click", () => { $("#plates-day").value = shiftedDate($("#plates-day").value || localDateValue(), 1); loadPlates().catch((error) => toast(error.message, true)); });
$("#plates-today").addEventListener("click", () => { $("#plates-day").value = localDateValue(); loadPlates().catch((error) => toast(error.message, true)); });
$("#events-prev").addEventListener("click", () => { state.eventOffset = Math.max(0, state.eventOffset - state.pageSize); loadEvents().catch((error) => toast(error.message, true)); });
$("#events-next").addEventListener("click", () => { state.eventOffset += state.pageSize; loadEvents().catch((error) => toast(error.message, true)); });
$("#drawer-close").addEventListener("click", closeDrawer);
$("#drawer-backdrop").addEventListener("click", closeDrawer);
$("#run-retention").addEventListener("click", runRetention);
$("#bollard-save-settings").addEventListener("click", saveBollardSettings);
$("#bollard-analyze").addEventListener("click", analyzeBollards);
$("#bollard-capture-baselines").addEventListener("click", async () => {
  if (!confirm("Erstatte alle tre faste referansebilder med nye nåbilder?")) return;
  const button = $("#bollard-capture-baselines");
  button.disabled = true;
  try {
    await api("/api/bollards/baselines", { method: "POST", body: "{}" });
    toast("Tre nye referansebilder er lagret");
    await loadBollards();
  } catch (error) { toast(error.message, true); }
  finally { button.disabled = false; }
});
$("#bollard-calibrator-close").addEventListener("click", closeBollardCalibrator);
$("#bollard-calibrator-cancel").addEventListener("click", closeBollardCalibrator);
$("#bollard-calibrator-backdrop").addEventListener("click", closeBollardCalibrator);
$("#bollard-calibrator-save").addEventListener("click", saveBollardCalibration);
$("#bollard-calibrator-reset").addEventListener("click", resetBollardPolygon);
$("#bollard-calibrator-undo").addEventListener("click", () => {
  if (!state.bollardDrawing?.polygonMode) return;
  state.bollardDrawing.points.pop();
  renderBollardPolygon();
});
$("#bollard-calibrator-refresh").addEventListener("click", () => {
  const drawing = state.bollardDrawing;
  if (!drawing?.polygonMode) return;
  drawing.source = `/api/bollards/cameras/${encodeURIComponent(drawing.cameraId)}/snapshot?v=${Date.now()}`;
  const image = $("img", drawing.frame);
  image.src = drawing.source;
  image.addEventListener("load", renderBollardPolygon, { once: true });
});
$("#refresh-button").addEventListener("click", refreshPage);
$("#copy-webhook").addEventListener("click", async () => {
  try { await navigator.clipboard.writeText($("#webhook-url").textContent); toast("Webhook-adressen er kopiert"); }
  catch (_) { toast("Kunne ikke kopiere automatisk", true); }
});
$("#build-filter-form").addEventListener("submit", (event) => { event.preventDefault(); loadBuilds().catch((error) => toast(error.message, true)); });
$("#build-clear").addEventListener("click", () => { $("#build-query").value = ""; loadBuilds().catch((error) => toast(error.message, true)); });
document.addEventListener("keydown", (event) => { if (event.key === "Escape") { closeDrawer(); if (!$("#bollard-calibrator").hidden) closeBollardCalibrator(); } });

async function boot() {
  setPage(currentPage());
  try {
    await loadCatalog();
    await loadOverview();
    if (currentPage() !== "dashboard") await refreshPage();
  } catch (error) { toast(`Kunne ikke laste appen: ${error.message}`, true); }
  setInterval(() => loadOverview().catch(() => {}), 15000);
}

boot();
