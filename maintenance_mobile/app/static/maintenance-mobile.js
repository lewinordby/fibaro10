const state = {
  bootstrap: null,
  targetType: "Seng",
  actionType: "Kontroll",
  selectedTags: new Set(),
  busy: false,
};

const $ = (selector) => document.querySelector(selector);

function safeText(value, fallback = "") {
  if (value === null || value === undefined) return fallback;
  const text = String(value).trim();
  return text || fallback;
}

function formatStamp(value) {
  if (!value) return "-";
  const parsed = new Date(String(value).replace(" ", "T"));
  if (Number.isNaN(parsed.getTime())) return String(value);
  return new Intl.DateTimeFormat("no-NO", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(parsed);
}

function optionList(key) {
  return (state.bootstrap?.options?.[key] || []).filter((item) => item && item.value);
}

function fillSelect(id, options, selectedValue, includeBlank = false) {
  const element = document.getElementById(id);
  if (!element) return;
  element.innerHTML = "";
  if (includeBlank) {
    const blank = document.createElement("option");
    blank.value = "";
    blank.textContent = "Ikke valgt";
    element.appendChild(blank);
  }
  for (const option of options) {
    const item = document.createElement("option");
    item.value = option.value;
    item.textContent = option.label;
    if (option.value === selectedValue) item.selected = true;
    element.appendChild(item);
  }
}

function renderChips(containerId, options, activeValue, onSelect, className = "") {
  const container = document.getElementById(containerId);
  if (!container) return;
  container.innerHTML = "";
  for (const option of options) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `choice-chip ${className} ${option.value === activeValue ? "is-active" : ""}`.trim();
    button.textContent = option.label;
    button.addEventListener("click", () => onSelect(option.value));
    container.appendChild(button);
  }
}

function renderTagChips() {
  const container = $("#tagChips");
  if (!container) return;
  container.innerHTML = "";
  const options = optionList("tags").slice(0, 18);
  for (const option of options) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `choice-chip tag-chip ${state.selectedTags.has(option.value) ? "is-active" : ""}`;
    button.textContent = option.label;
    button.addEventListener("click", () => {
      if (state.selectedTags.has(option.value)) state.selectedTags.delete(option.value);
      else state.selectedTags.add(option.value);
      renderTagChips();
    });
    container.appendChild(button);
  }
}

function renderStatusCards() {
  const container = $("#statusCards");
  if (!container) return;
  const cards = (state.bootstrap?.cards || []).slice(0, 4);
  container.innerHTML = cards.map((card) => `
    <article class="status-card">
      <span>${safeText(card.label)}</span>
      <strong>${safeText(card.value, "-")}${card.unit ? ` ${safeText(card.unit)}` : ""}</strong>
      <small>${safeText(card.detail)}</small>
    </article>
  `).join("");
}

function renderRecent() {
  const container = $("#recentList");
  if (!container) return;
  const rows = state.bootstrap?.recent || [];
  if (!rows.length) {
    container.innerHTML = '<p class="muted">Ingen vedlikeholdsposter ennå.</p>';
    return;
  }
  container.innerHTML = rows.map((row) => {
    const target = [row.target_type, row.target_name].filter(Boolean).join(" · ");
    const meta = [
      formatStamp(row.performed_at),
      safeText(row.action_type),
      safeText(row.priority),
      safeText(row.performed_by),
    ].filter(Boolean).join(" · ");
    const statusClass = row.follow_up_needed ? "is-open" : "";
    return `
      <article class="recent-item">
        <div class="recent-main">
          <strong>${safeText(row.summary, "Uten notat")}</strong>
          <span class="recent-meta">${safeText(target, "Generelt")}</span>
          <span class="recent-meta">${meta}</span>
          ${row.tags ? `<span class="recent-tags">${safeText(row.tags)}</span>` : ""}
        </div>
        <span class="recent-status ${statusClass}">${row.follow_up_needed ? "Oppfølging" : safeText(row.status, "Utført")}</span>
      </article>
    `;
  }).join("");
}

function setTargetType(value) {
  state.targetType = value || "Generelt";
  renderChips("targetChips", optionList("target_type"), state.targetType, setTargetType);
}

function setActionType(value) {
  state.actionType = value || "Kontroll";
  renderChips("actionChips", optionList("action_type"), state.actionType, setActionType);
}

function setDefaults() {
  const defaults = state.bootstrap?.defaults || {};
  const now = new Date();
  now.setSeconds(0, 0);
  const localFallback = new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
  $("#performed_at").value = defaults.performed_at || localFallback;
  $("#performed_by").value = safeText(state.bootstrap?.user?.username);
  fillSelect("presence_type", optionList("presence_type"), defaults.presence_type || "Tilstede Sun2");
  fillSelect("room_id", optionList("room_id"), "", true);
  fillSelect("priority", optionList("priority"), defaults.priority || "Normal");
  fillSelect("status", optionList("status"), defaults.status || "Utført");
  state.targetType = defaults.target_type || "Seng";
  state.actionType = defaults.action_type || "Kontroll";
  state.selectedTags = new Set();
  setTargetType(state.targetType);
  setActionType(state.actionType);
  renderTagChips();
}

function updateHeader() {
  const user = safeText(state.bootstrap?.user?.username, "ukjent bruker");
  const role = safeText(state.bootstrap?.user?.roleLabel || state.bootstrap?.user?.role, "innlogget");
  $("#userLine").textContent = `${user} · ${role} · lagres direkte i Fibaro10`;
}

async function loadBootstrap() {
  const response = await fetch("/api/bootstrap", { credentials: "same-origin" });
  if (response.status === 401) {
    window.location.href = "/auth/login";
    return;
  }
  if (!response.ok) throw new Error(await response.text());
  state.bootstrap = await response.json();
  updateHeader();
  setDefaults();
  renderStatusCards();
  renderRecent();
}

function splitTags(value) {
  return String(value || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function formPayload() {
  const customTags = splitTags($("#custom_tags").value);
  const tags = [...state.selectedTags, ...customTags];
  return {
    performed_at: $("#performed_at").value,
    performed_by: $("#performed_by").value,
    presence_type: $("#presence_type").value,
    target_type: state.targetType,
    room_id: $("#room_id").value || null,
    target_name: $("#target_name").value,
    action_type: state.actionType,
    priority: $("#priority").value,
    status: $("#status").value,
    summary: $("#summary").value,
    tags,
    duration_minutes: $("#duration_minutes").value ? Number($("#duration_minutes").value) : null,
    follow_up_needed: $("#follow_up_needed").checked,
    follow_up_text: $("#follow_up_text").value,
  };
}

function resetFormAfterSave() {
  $("#summary").value = "";
  $("#target_name").value = "";
  $("#room_id").value = "";
  $("#custom_tags").value = "";
  $("#duration_minutes").value = "";
  $("#follow_up_needed").checked = false;
  $("#follow_up_text").value = "";
  setDefaults();
}

function setMessage(message, isError = false) {
  const element = $("#formMessage");
  element.textContent = message || "";
  element.classList.toggle("is-error", Boolean(isError));
}

async function submitForm(event) {
  event.preventDefault();
  if (state.busy) return;
  state.busy = true;
  $("#submitButton").disabled = true;
  setMessage("Lagrer...");
  try {
    const response = await fetch("/api/maintenance/logs", {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(formPayload()),
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.detail || payload.message || "Kunne ikke lagre.");
    setMessage(payload.message || "Lagret.");
    resetFormAfterSave();
    await loadBootstrap();
  } catch (error) {
    setMessage(error.message || String(error), true);
  } finally {
    state.busy = false;
    $("#submitButton").disabled = false;
  }
}

document.addEventListener("DOMContentLoaded", async () => {
  $("#maintenanceForm").addEventListener("submit", submitForm);
  $("#refreshButton").addEventListener("click", () => loadBootstrap().catch((error) => setMessage(error.message, true)));
  try {
    await loadBootstrap();
  } catch (error) {
    setMessage(error.message || String(error), true);
  }
});
