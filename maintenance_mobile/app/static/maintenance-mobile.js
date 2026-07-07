const TASKS = [
  {
    key: "vacuum-clean",
    code: "RV",
    title: "Rens støvsugere",
    detail: "Renhold",
    category: "Renhold",
    targetType: "Renhold",
    targetName: "Støvsugere",
    actionType: "Rengjøring",
    priority: "Normal",
    status: "Utført",
    summary: "Rens støvsugere",
    durationMinutes: 10,
    initialFocus: "summary",
    tags: ["Renhold", "Støvsugere", "Rens", "Rutine", "Mobil"],
  },
  {
    key: "bed-check",
    code: "SS",
    title: "Sjekk solseng",
    detail: "Seng",
    category: "Soling",
    targetType: "Seng",
    actionType: "Kontroll",
    priority: "Normal",
    status: "Utført",
    summary: "Sjekk solseng",
    requiresRoom: true,
    initialFocus: "room",
    tags: ["Soling", "Seng", "Kontroll", "Mobil"],
  },
  {
    key: "bed-clean",
    code: "RS",
    title: "Rengjør seng",
    detail: "Seng",
    category: "Renhold",
    targetType: "Seng",
    actionType: "Rengjøring",
    priority: "Normal",
    status: "Utført",
    summary: "Rengjør seng",
    requiresRoom: true,
    initialFocus: "room",
    tags: ["Renhold", "Soling", "Seng", "Mobil"],
  },
  {
    key: "tube-change",
    code: "BR",
    title: "Bytt rør",
    detail: "Seng",
    category: "Teknisk",
    targetType: "Seng",
    actionType: "Bytte",
    priority: "Høy",
    status: "Utført",
    summary: "Bytt rør",
    requiresRoom: true,
    initialFocus: "room",
    tags: ["Teknisk", "Seng", "Rør", "Bytte", "Mobil"],
  },
  {
    key: "ventilation-check",
    code: "VE",
    title: "Sjekk ventilasjon",
    detail: "Bygg",
    category: "Drift",
    targetType: "Ventilasjon",
    actionType: "Kontroll",
    priority: "Normal",
    status: "Utført",
    summary: "Sjekk ventilasjon",
    initialFocus: "summary",
    tags: ["Ventilasjon", "Kontroll", "Mobil"],
  },
  {
    key: "light-check",
    code: "LY",
    title: "Sjekk lys",
    detail: "Bygg",
    category: "Drift",
    targetType: "Lys",
    actionType: "Kontroll",
    priority: "Normal",
    status: "Utført",
    summary: "Sjekk lys",
    initialFocus: "summary",
    tags: ["Lys", "Kontroll", "Mobil"],
  },
  {
    key: "supplies-refill",
    code: "PF",
    title: "Fyll forbruk",
    detail: "Utstyr",
    category: "Drift",
    targetType: "Utstyr",
    targetName: "Forbruksmateriell",
    actionType: "Påfyll",
    priority: "Normal",
    status: "Utført",
    summary: "Fyll forbruksmateriell",
    initialFocus: "summary",
    tags: ["Utstyr", "Påfyll", "Innkjøp", "Mobil"],
  },
  {
    key: "other-deviation",
    code: "AV",
    title: "Annet avvik",
    detail: "Oppfølging",
    category: "Avvik",
    targetType: "Generelt",
    actionType: "Observasjon",
    priority: "Høy",
    status: "Må følges opp",
    summary: "Avvik eller observasjon",
    followUpNeeded: true,
    initialFocus: "followUp",
    tags: ["Avvik", "Oppfølging", "Mobil"],
  },
];

const state = {
  bootstrap: null,
  selectedTask: null,
  busy: false,
  lastSavedTitle: "",
};

const $ = (selector) => document.querySelector(selector);

function safeText(value, fallback = "") {
  if (value === null || value === undefined) return fallback;
  const text = String(value).trim();
  return text || fallback;
}

function normalizeToken(value) {
  return safeText(value).toLocaleLowerCase("nb-NO");
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

function formatTimeButton(value) {
  if (!value) return "Nå";
  const parsed = new Date(String(value).replace(" ", "T"));
  if (Number.isNaN(parsed.getTime())) return String(value);
  const today = new Date();
  const sameDate = parsed.toDateString() === today.toDateString();
  const time = new Intl.DateTimeFormat("no-NO", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(parsed);
  if (sameDate) return `I dag ${time}`;
  const date = new Intl.DateTimeFormat("no-NO", {
    day: "2-digit",
    month: "2-digit",
  }).format(parsed);
  return `${date} ${time}`;
}

function localDateTimeValue(value) {
  if (value) return String(value).slice(0, 16);
  const now = new Date();
  now.setSeconds(0, 0);
  return new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
}

function optionList(key) {
  return (state.bootstrap?.options?.[key] || []).filter((item) => item && item.value);
}

function hasOption(key, value) {
  return optionList(key).some((option) => option.value === value);
}

function validOption(key, value, fallback) {
  return hasOption(key, value) ? value : fallback;
}

function shortText(value, maxLength = 46) {
  const text = safeText(value);
  if (text.length <= maxLength) return text;
  return `${text.slice(0, maxLength - 1)}…`;
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

function showScreen(screenName) {
  $("#taskScreen")?.classList.toggle("is-hidden", screenName !== "tasks");
  $("#entryScreen")?.classList.toggle("is-hidden", screenName !== "entry");
  document.body.classList.toggle("entry-mode", screenName === "entry");
  setMessage("");
  if (screenName === "entry") setTaskMessage("");
}

function renderTasks() {
  const container = $("#taskGrid");
  if (!container) return;
  container.innerHTML = TASKS.map((task) => `
    <button class="task-button" type="button" data-task-key="${task.key}">
      <span class="task-code">${task.code}</span>
      <span class="task-title">${task.title}</span>
      <span class="task-detail">${task.detail}</span>
    </button>
  `).join("");
  container.querySelectorAll("[data-task-key]").forEach((button) => {
    button.addEventListener("click", () => openTask(button.dataset.taskKey));
  });
}

function roomLabel(value) {
  const match = optionList("room_id").find((option) => option.value === value);
  return safeText(match?.label, value);
}

function renderRoomChoices() {
  const container = $("#roomQuickGrid");
  if (!container) return;
  const selected = $("#room_id")?.value || "";
  const rooms = optionList("room_id");
  container.innerHTML = rooms.map((room) => `
    <button class="room-chip ${room.value === selected ? "is-active" : ""}" type="button" data-room-id="${room.value}">
      ${safeText(room.label, room.value)}
    </button>
  `).join("");
  container.querySelectorAll("[data-room-id]").forEach((button) => {
    button.addEventListener("click", () => selectRoom(button.dataset.roomId || ""));
  });
}

function selectRoom(value) {
  const element = $("#room_id");
  if (!element) return;
  element.value = value || "";
  renderRoomChoices();
  updateSubmitState();
}

function automaticTags(task) {
  const performedAt = $("#performed_at")?.value || "";
  const datePart = performedAt.slice(0, 10);
  const tags = [
    ...(task.tags || []),
    task.category,
    task.targetType,
    task.actionType,
    "Mobil",
  ];
  if (datePart) tags.push(`Dato ${datePart}`);
  const selectedRoom = $("#room_id")?.value;
  if (selectedRoom) tags.push(roomLabel(selectedRoom));
  return [...new Set(tags.filter(Boolean))].slice(0, 20);
}

function setFollowUpVisible() {
  const checked = Boolean($("#follow_up_needed")?.checked);
  $("#followUpField")?.classList.toggle("is-hidden", !checked);
}

function setTimeFieldVisible(visible) {
  $("#timeField")?.classList.toggle("is-hidden", !visible);
  $("#timeButton")?.setAttribute("aria-expanded", visible ? "true" : "false");
}

function updateTimeButton() {
  const label = $("#timeButtonLabel");
  if (label) label.textContent = formatTimeButton($("#performed_at")?.value);
}

function setNoteFieldVisible(visible, focus = false) {
  $("#noteField")?.classList.toggle("is-hidden", !visible);
  $("#noteButton")?.setAttribute("aria-expanded", visible ? "true" : "false");
  if (visible && focus) setTimeout(() => $("#summary")?.focus(), 40);
}

function focusAfterScreenChange(selector, { select = false, scroll = true } = {}) {
  window.setTimeout(() => {
    const element = $(selector);
    if (!element) return;
    if (scroll && typeof element.scrollIntoView === "function") {
      element.scrollIntoView({ block: "center", behavior: "smooth" });
    }
    try {
      element.focus({ preventScroll: true });
    } catch {
      element.focus();
    }
    if (select && typeof element.select === "function") element.select();
  }, 120);
}

function focusInitialTaskField(task) {
  const target = task.initialFocus || (task.requiresRoom ? "room" : task.followUpNeeded ? "followUp" : "summary");
  if (target === "room") {
    focusAfterScreenChange("#roomQuickGrid .room-chip", { scroll: true });
    return;
  }
  if (target === "followUp") {
    $("#follow_up_needed").checked = true;
    setFollowUpVisible();
    focusAfterScreenChange("#follow_up_text", { scroll: true });
    return;
  }
  if (target === "duration") {
    focusAfterScreenChange("#duration_minutes", { select: true, scroll: true });
    return;
  }
  if (target === "time") {
    setTimeFieldVisible(true);
    focusAfterScreenChange("#performed_at", { select: true, scroll: true });
    return;
  }
  if (target === "submit") {
    focusAfterScreenChange("#submitButton", { scroll: true });
    return;
  }
  setNoteFieldVisible(true, false);
  focusAfterScreenChange("#summary", { select: true, scroll: true });
}

function updateNotePreview() {
  const preview = $("#notePreview");
  if (preview) preview.textContent = shortText($("#summary")?.value || state.selectedTask?.summary || "Standardtekst");
}

function updateSubmitState() {
  const button = $("#submitButton");
  if (!button) return;
  const needsRoom = Boolean(state.selectedTask?.requiresRoom);
  const missingRoom = needsRoom && !$("#room_id")?.value;
  button.disabled = state.busy || missingRoom;
  if (state.busy) {
    button.textContent = "Lagrer...";
  } else if (missingRoom) {
    button.textContent = "Velg seng / rom";
  } else {
    button.textContent = `Lagre ${state.selectedTask?.title || ""}`.trim();
  }
}

function setTaskDefaults(task) {
  const defaults = state.bootstrap?.defaults || {};
  const user = safeText(state.bootstrap?.user?.username);
  $("#performed_at").value = localDateTimeValue(defaults.performed_at);
  $("#performed_by").value = user;
  $("#entryUserLine").textContent = user ? `Registreres av ${user}` : "";
  setTimeFieldVisible(false);
  updateTimeButton();
  fillSelect("room_id", optionList("room_id"), "", true);
  renderRoomChoices();
  $("#roomField").classList.toggle("is-hidden", !task.requiresRoom);
  $("#summary").value = task.summary || task.title;
  setNoteFieldVisible(false);
  updateNotePreview();
  $("#duration_minutes").value = task.durationMinutes ? String(task.durationMinutes) : "";
  $("#follow_up_needed").checked = Boolean(task.followUpNeeded);
  $("#follow_up_text").value = "";
  setFollowUpVisible();
  updateSubmitState();
}

function openTask(taskKey) {
  const task = TASKS.find((item) => item.key === taskKey);
  if (!task) return;
  state.selectedTask = task;
  $("#taskCategory").textContent = task.category || "Oppgave";
  $("#taskTitle").textContent = task.title;
  $("#taskSubtitle").textContent = task.requiresRoom ? "Velg seng/rom og lagre posten." : "Fyll eventuelt inn notat og lagre posten.";
  setTaskDefaults(task);
  showScreen("entry");
  renderRecent();
  focusInitialTaskField(task);
}

function rowTags(row) {
  return safeText(row.tags)
    .split(",")
    .map((tag) => normalizeToken(tag))
    .filter(Boolean);
}

function recentRowMatchesTask(row, task) {
  if (!task) return true;
  const tags = rowTags(row);
  const category = normalizeToken(task.category);
  if (category && tags.includes(category)) return true;
  if (category && tags.length) return false;
  const targetType = normalizeToken(row.target_type);
  const actionType = normalizeToken(row.action_type);
  const targetName = normalizeToken(row.target_name);
  const taskTargetType = normalizeToken(task.targetType);
  const taskActionType = normalizeToken(task.actionType);
  const taskTargetName = normalizeToken(task.targetName);
  if (taskTargetType && taskActionType && targetType === taskTargetType && actionType === taskActionType) return true;
  if (taskTargetName && targetName.includes(taskTargetName)) return true;
  return false;
}

function filteredRecentRows() {
  const rows = state.bootstrap?.recent || [];
  if (!state.selectedTask) return rows.slice(0, 12);
  return rows.filter((row) => recentRowMatchesTask(row, state.selectedTask)).slice(0, 12);
}

function renderRecent() {
  const container = $("#recentList");
  if (!container) return;
  const rows = filteredRecentRows();
  const title = $("#recentTitle");
  const subtitle = $("#recentSubtitle");
  if (state.selectedTask) {
    if (title) title.textContent = `Siste ${state.selectedTask.category || state.selectedTask.title}`;
    if (subtitle) subtitle.textContent = `Viser bare poster som hører til ${state.selectedTask.category || "valgt oppgave"}.`;
  } else {
    if (title) title.textContent = "Siste registreringer";
    if (subtitle) subtitle.textContent = "Siste vedlikeholdsposter på tvers av kategorier.";
  }
  if (!rows.length) {
    const emptyText = state.selectedTask
      ? `Ingen tidligere poster i ${state.selectedTask.category || state.selectedTask.title}.`
      : "Ingen vedlikeholdsposter ennå.";
    container.innerHTML = `<p class="muted">${emptyText}</p>`;
    return;
  }
  container.innerHTML = rows.map((row) => {
    const target = [row.target_type, row.target_name].filter(Boolean).join(" - ");
    const meta = [
      formatStamp(row.performed_at),
      safeText(row.action_type),
      safeText(row.priority),
      safeText(row.performed_by),
    ].filter(Boolean).join(" - ");
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

function updateHeader() {
  const user = safeText(state.bootstrap?.user?.username, "ukjent bruker");
  const role = safeText(state.bootstrap?.user?.roleLabel || state.bootstrap?.user?.role, "innlogget");
  $("#userLine").textContent = `${user} - ${role} - lagres i Fibaro10`;
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
  renderTasks();
  renderRecent();
}

function formPayload() {
  const task = state.selectedTask;
  if (!task) throw new Error("Velg en oppgave først.");
  const followUpNeeded = Boolean($("#follow_up_needed").checked);
  const statusValue = followUpNeeded
    ? "Må følges opp"
    : (task.status === "Må følges opp" ? "Utført" : (task.status || "Utført"));
  const user = safeText($("#performed_by")?.value, safeText(state.bootstrap?.user?.username));
  return {
    performed_at: $("#performed_at").value,
    performed_by: user,
    presence_type: validOption("presence_type", task.presenceType || "Tilstede Sun2", "Tilstede Sun2"),
    target_type: validOption("target_type", task.targetType || "Generelt", "Generelt"),
    room_id: task.requiresRoom ? ($("#room_id").value || null) : null,
    target_name: task.targetName || "",
    action_type: validOption("action_type", task.actionType || "Kontroll", "Kontroll"),
    priority: validOption("priority", task.priority || "Normal", "Normal"),
    status: validOption("status", statusValue, "Utført"),
    summary: safeText($("#summary").value, task.summary || task.title),
    tags: automaticTags(task),
    duration_minutes: $("#duration_minutes").value ? Number($("#duration_minutes").value) : null,
    follow_up_needed: followUpNeeded,
    follow_up_text: $("#follow_up_text").value,
  };
}

function setMessage(message, isError = false) {
  const element = $("#formMessage");
  if (!element) return;
  element.textContent = message || "";
  element.classList.toggle("is-error", Boolean(isError));
}

function setTaskMessage(message, isError = false) {
  const element = $("#taskMessage");
  if (!element) return;
  element.textContent = message || "";
  element.classList.toggle("is-error", Boolean(isError));
  element.classList.toggle("is-hidden", !message);
}

async function submitForm(event) {
  event.preventDefault();
  if (state.busy) return;
  if (state.selectedTask?.requiresRoom && !$("#room_id")?.value) {
    setMessage("Velg seng / rom før du lagrer.", true);
    updateSubmitState();
    return;
  }
  const savedTitle = state.selectedTask?.title || "Vedlikehold";
  state.busy = true;
  updateSubmitState();
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
    state.lastSavedTitle = savedTitle;
    state.selectedTask = null;
    await loadBootstrap();
    showScreen("tasks");
    setTaskMessage(`Lagret: ${savedTitle}`);
  } catch (error) {
    setMessage(error.message || String(error), true);
  } finally {
    state.busy = false;
    updateSubmitState();
  }
}

document.addEventListener("DOMContentLoaded", async () => {
  $("#maintenanceForm")?.addEventListener("submit", submitForm);
  $("#backButton")?.addEventListener("click", () => {
    state.selectedTask = null;
    showScreen("tasks");
    renderRecent();
  });
  $("#refreshButton")?.addEventListener("click", () => loadBootstrap().catch((error) => setMessage(error.message, true)));
  $("#follow_up_needed")?.addEventListener("change", setFollowUpVisible);
  $("#room_id")?.addEventListener("change", () => {
    renderRoomChoices();
    updateSubmitState();
  });
  $("#noteButton")?.addEventListener("click", () => {
    const field = $("#noteField");
    const visible = field?.classList.contains("is-hidden");
    setNoteFieldVisible(Boolean(visible), Boolean(visible));
  });
  $("#summary")?.addEventListener("input", updateNotePreview);
  $("#timeButton")?.addEventListener("click", () => {
    const field = $("#timeField");
    const visible = field?.classList.contains("is-hidden");
    setTimeFieldVisible(Boolean(visible));
    if (visible) setTimeout(() => $("#performed_at")?.focus(), 40);
  });
  $("#performed_at")?.addEventListener("change", updateTimeButton);
  try {
    await loadBootstrap();
    showScreen("tasks");
  } catch (error) {
    setMessage(error.message || String(error), true);
  }
});
