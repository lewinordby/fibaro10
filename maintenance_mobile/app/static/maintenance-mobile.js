const LEGACY_TASKS = [
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

const HEAT_PUMP_TARGETS = [
  { value: "1.etg", label: "1.etg" },
  { value: "2.etg", label: "2.etg" },
  { value: "VIP", label: "VIP" },
];

const HEAT_PUMP_STANDARD_TASKS = ["Renset filter", "Endret innstilling"];

const TASKS = [
  {
    key: "robot-cleaners",
    title: "Robotvaskere",
    category: "Renhold",
    targetType: "Utstyr",
    targetName: "Robotvaskere",
    actionType: "Vedlikehold",
    priority: "Normal",
    status: "Utført",
    summary: "Robotvaskere",
    requiresRobots: true,
    standardTasks: ["Rengjort", "Rengjort brett", "Skiftet mopper", "Skiftet valse"],
    defaultStandardTasks: ["Rengjort"],
    initialFocus: "robots",
    tags: ["Renhold", "Utstyr", "Robotvaskere", "Mobil"],
  },
  {
    key: "heat-pumps",
    title: "Varmepumper",
    category: "Drift",
    targetType: "Ventilasjon",
    targetName: "Varmepumper",
    actionType: "Kontroll",
    priority: "Normal",
    status: "Utført",
    summary: "Varmepumper",
    targetChoices: HEAT_PUMP_TARGETS,
    targetChoiceLabel: "Varmepumper",
    allTargetName: "Alle varmepumper",
    standardTasks: HEAT_PUMP_STANDARD_TASKS,
    defaultStandardTasks: ["Renset filter"],
    initialFocus: "targetChoices",
    tags: ["Ventilasjon", "Varmepumper", "Kontroll", "Mobil"],
  },
  {
    key: "sunbeds",
    title: "Solsenger",
    category: "Soling",
    targetType: "Seng",
    actionType: "Vedlikehold",
    priority: "Normal",
    status: "Utført",
    summary: "Solsenger",
    requiresRoom: true,
    initialFocus: "room",
    tags: ["Soling", "Seng", "Vedlikehold", "Mobil"],
  },
  {
    key: "cream-machine",
    title: "Kremautomat",
    category: "Drift",
    targetType: "Utstyr",
    targetName: "Kremautomat",
    actionType: "Vedlikehold",
    priority: "Normal",
    status: "Utført",
    summary: "Kremautomat",
    initialFocus: "summary",
    tags: ["Utstyr", "Kremautomat", "Vedlikehold", "Mobil"],
  },
  {
    key: "other",
    title: "Annet",
    category: "Avvik",
    targetType: "Generelt",
    actionType: "Observasjon",
    priority: "Normal",
    status: "Utført",
    summary: "Annet",
    initialFocus: "summary",
    tags: ["Avvik", "Observasjon", "Mobil"],
  },
];

const state = {
  bootstrap: null,
  selectedTask: null,
  editingLog: null,
  selectedRobots: [],
  selectedTargetChoices: [],
  selectedStandardTasks: [],
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

function currentUsername() {
  return safeText(state.bootstrap?.user?.username);
}

function isOwnLog(row) {
  return normalizeToken(row?.performed_by) === normalizeToken(currentUsername());
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
  $("#profileScreen")?.classList.toggle("is-hidden", screenName !== "profile");
  $("#recentCard")?.classList.toggle("is-hidden", screenName === "profile");
  document.body.classList.toggle("entry-mode", screenName === "entry");
  document.body.classList.toggle("profile-mode", screenName === "profile");
  setMessage("");
  if (screenName === "entry" || screenName === "profile") setTaskMessage("");
}

function renderTasks() {
  const container = $("#taskGrid");
  if (!container) return;
  container.innerHTML = TASKS.map((task) => `
    <button class="task-button" type="button" data-task-key="${task.key}">
      <span class="task-title">${task.title}</span>
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

function robotLabel(value) {
  const match = optionList("robots").find((option) => option.value === value);
  return safeText(match?.label, value);
}

function targetChoiceOptions(task = state.selectedTask) {
  return (task?.targetChoices || []).map((option) => {
    if (typeof option === "string") return { value: option, label: option };
    return {
      value: safeText(option.value, safeText(option.label)),
      label: safeText(option.label, safeText(option.value)),
    };
  }).filter((option) => option.value);
}

function targetChoiceLabel(value) {
  const match = targetChoiceOptions().find((option) => option.value === value);
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

function renderRobotChoices() {
  const container = $("#robotQuickGrid");
  if (!container) return;
  const robots = optionList("robots");
  const selected = new Set(state.selectedRobots);
  if (!robots.length) {
    container.innerHTML = `<p class="muted">Ingen robotnavn funnet fra Roborock.</p>`;
    return;
  }
  container.innerHTML = robots.map((robot) => `
    <button class="robot-chip ${selected.has(robot.value) ? "is-active" : ""}" type="button" data-robot-id="${robot.value}">
      ${safeText(robot.label, robot.value)}
    </button>
  `).join("");
  container.querySelectorAll("[data-robot-id]").forEach((button) => {
    button.addEventListener("click", () => toggleRobot(button.dataset.robotId || ""));
  });
  updateRobotAllButton();
}

function updateRobotAllButton() {
  const button = $("#robotAllButton");
  if (!button) return;
  const robots = optionList("robots");
  const allSelected = robots.length > 0 && state.selectedRobots.length === robots.length;
  button.textContent = allSelected ? "Fjern alle" : "Alle";
}

function renderTargetChoices() {
  const container = $("#targetChoiceGrid");
  if (!container) return;
  const options = targetChoiceOptions();
  const selected = new Set(state.selectedTargetChoices);
  $("#targetChoiceLabel").textContent = state.selectedTask?.targetChoiceLabel || "Valg";
  container.innerHTML = options.map((option) => `
    <button class="target-choice-chip ${selected.has(option.value) ? "is-active" : ""}" type="button" data-target-choice="${option.value}">
      ${safeText(option.label, option.value)}
    </button>
  `).join("");
  container.querySelectorAll("[data-target-choice]").forEach((button) => {
    button.addEventListener("click", () => toggleTargetChoice(button.dataset.targetChoice || ""));
  });
  updateTargetChoiceAllButton();
}

function updateTargetChoiceAllButton() {
  const button = $("#targetChoiceAllButton");
  if (!button) return;
  const options = targetChoiceOptions();
  const allSelected = options.length > 0 && state.selectedTargetChoices.length === options.length;
  button.textContent = allSelected ? "Fjern alle" : "Alle";
}

function selectRoom(value) {
  const element = $("#room_id");
  if (!element) return;
  element.value = value || "";
  renderRoomChoices();
  updateSubmitState();
}

function toggleRobot(value) {
  if (!value) return;
  const selected = new Set(state.selectedRobots);
  if (selected.has(value)) {
    selected.delete(value);
  } else {
    selected.add(value);
  }
  state.selectedRobots = [...selected];
  renderRobotChoices();
  updateSubmitState();
}

function toggleAllRobots() {
  const robots = optionList("robots").map((robot) => robot.value);
  if (!robots.length) return;
  state.selectedRobots = state.selectedRobots.length === robots.length ? [] : robots;
  renderRobotChoices();
  updateSubmitState();
}

function selectedRobotLabels() {
  return state.selectedRobots.map(robotLabel).filter(Boolean);
}

function toggleTargetChoice(value) {
  if (!value) return;
  const selected = new Set(state.selectedTargetChoices);
  if (selected.has(value)) {
    selected.delete(value);
  } else {
    selected.add(value);
  }
  state.selectedTargetChoices = [...selected];
  renderTargetChoices();
  updateSubmitState();
}

function toggleAllTargetChoices() {
  const options = targetChoiceOptions().map((option) => option.value);
  if (!options.length) return;
  state.selectedTargetChoices = state.selectedTargetChoices.length === options.length ? [] : options;
  renderTargetChoices();
  updateSubmitState();
}

function selectedTargetChoiceLabels(task = state.selectedTask) {
  const allowed = new Set(targetChoiceOptions(task).map((item) => normalizeToken(item.value)));
  return state.selectedTargetChoices
    .filter((item) => !allowed.size || allowed.has(normalizeToken(item)))
    .map(targetChoiceLabel)
    .filter(Boolean);
}

function renderStandardTaskChoices() {
  const container = $("#standardTaskGrid");
  if (!container) return;
  const tasks = state.selectedTask?.standardTasks || [];
  const selected = new Set(state.selectedStandardTasks);
  if (!tasks.length) {
    container.innerHTML = "";
    return;
  }
  container.innerHTML = tasks.map((task) => `
    <button class="standard-task-chip ${selected.has(task) ? "is-active" : ""}" type="button" data-standard-task="${task}">
      ${task}
    </button>
  `).join("");
  container.querySelectorAll("[data-standard-task]").forEach((button) => {
    button.addEventListener("click", () => toggleStandardTask(button.dataset.standardTask || ""));
  });
}

function toggleStandardTask(value) {
  if (!value) return;
  const selected = new Set(state.selectedStandardTasks);
  if (selected.has(value)) {
    selected.delete(value);
  } else {
    selected.add(value);
  }
  state.selectedStandardTasks = [...selected];
  renderStandardTaskChoices();
  updateSubmitState();
}

function selectedStandardTaskLabels() {
  const allowed = new Set((state.selectedTask?.standardTasks || []).map((item) => normalizeToken(item)));
  return state.selectedStandardTasks.filter((item) => !allowed.size || allowed.has(normalizeToken(item)));
}

function standardTasksFromLog(row, taskList) {
  const tags = rowTags(row);
  const summary = normalizeToken(row.summary);
  return taskList.filter((item) => {
    const token = normalizeToken(item);
    return tags.includes(token) || summary.includes(token);
  });
}

function autoSummaryForTask(task, standardTaskLabels, robotLabels, allRobotsSelected, targetChoiceLabels, allTargetChoicesSelected) {
  const parts = [];
  if (standardTaskLabels.length) parts.push(standardTaskLabels.join(", "));
  if (task.requiresRobots && robotLabels.length) {
    parts.push(allRobotsSelected ? "alle robotvaskere" : robotLabels.join(", "));
  }
  if (targetChoiceLabels.length) {
    parts.push(allTargetChoicesSelected ? (task.allTargetName || "Alle") : targetChoiceLabels.join(", "));
  }
  return parts.length ? `${task.title}: ${parts.join(" - ")}` : (task.summary || task.title);
}

function automaticTags(task) {
  const performedAt = $("#performed_at")?.value || "";
  const datePart = performedAt.slice(0, 10);
  const tags = state.editingLog
    ? [...(task.tags || []), "Mobil"]
    : [
        ...(task.tags || []),
        task.category,
        task.targetType,
        task.actionType,
        "Mobil",
      ];
  if (datePart) tags.push(`Dato ${datePart}`);
  const selectedRoom = $("#room_id")?.value;
  if (selectedRoom) tags.push(roomLabel(selectedRoom));
  for (const robot of selectedRobotLabels()) tags.push(robot);
  for (const targetChoice of selectedTargetChoiceLabels(task)) tags.push(targetChoice);
  for (const standardTask of selectedStandardTaskLabels()) tags.push(standardTask);
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
  $("#noteField")?.classList.remove("is-hidden");
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
  if (target === "robots") {
    focusAfterScreenChange("#robotQuickGrid .robot-chip", { scroll: true });
    return;
  }
  if (target === "targetChoices") {
    focusAfterScreenChange("#targetChoiceGrid .target-choice-chip", { scroll: true });
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

function updateSubmitState() {
  const button = $("#submitButton");
  if (!button) return;
  const needsRoom = Boolean(state.selectedTask?.requiresRoom);
  const missingRoom = needsRoom && !$("#room_id")?.value;
  const needsRobots = Boolean(state.selectedTask?.requiresRobots);
  const missingRobots = needsRobots && optionList("robots").length > 0 && state.selectedRobots.length === 0;
  const needsTargetChoices = targetChoiceOptions(state.selectedTask).length > 0;
  const missingTargetChoices = needsTargetChoices && state.selectedTargetChoices.length === 0;
  const needsStandardTask = (state.selectedTask?.standardTasks || []).length > 0;
  const missingStandardTask = needsStandardTask && state.selectedStandardTasks.length === 0;
  button.disabled = state.busy || missingRoom || missingRobots || missingTargetChoices || missingStandardTask;
  if (state.busy) {
    button.textContent = "Lagrer...";
  } else if (missingRoom) {
    button.textContent = "Velg seng / rom";
  } else if (missingRobots) {
    button.textContent = "Velg robotvasker";
  } else if (missingTargetChoices) {
    button.textContent = `Velg ${state.selectedTask?.targetChoiceLabel || "valg"}`;
  } else if (missingStandardTask) {
    button.textContent = "Velg oppgave";
  } else if (state.editingLog) {
    button.textContent = "Lagre endring";
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
  state.selectedRobots = [];
  $("#robotField").classList.toggle("is-hidden", !task.requiresRobots);
  renderRobotChoices();
  state.selectedTargetChoices = [];
  $("#targetChoiceField").classList.toggle("is-hidden", !targetChoiceOptions(task).length);
  renderTargetChoices();
  state.selectedStandardTasks = [...(task.defaultStandardTasks || [])];
  $("#standardTaskField").classList.toggle("is-hidden", !(task.standardTasks || []).length);
  renderStandardTaskChoices();
  $("#summary").value = task.summary || task.title;
  setNoteFieldVisible(true);
  $("#duration_minutes").value = task.durationMinutes ? String(task.durationMinutes) : "";
  $("#follow_up_needed").checked = Boolean(task.followUpNeeded);
  $("#follow_up_text").value = "";
  setFollowUpVisible();
  updateSubmitState();
}

function taskFromLog(row) {
  const targetType = safeText(row.target_type, "Generelt");
  const actionType = safeText(row.action_type, "Kontroll");
  const summary = safeText(row.summary, actionType);
  const requiresRoom = Boolean(row.room_id);
  const tags = rowTags(row);
  const robotValues = optionList("robots").map((robot) => robot.value);
  const selectedRobots = robotValues.filter((robot) => {
    const token = normalizeToken(robot);
    return tags.includes(token) || normalizeToken(row.target_name).includes(token);
  });
  const requiresRobots = selectedRobots.length > 0 || normalizeToken(targetType) === "utstyr" && normalizeToken(row.target_name).includes("robot");
  const targetNameToken = normalizeToken(row.target_name);
  const summaryToken = normalizeToken(summary);
  const selectedTargetChoices = HEAT_PUMP_TARGETS
    .filter((option) => {
      const token = normalizeToken(option.value);
      return tags.includes(token) || targetNameToken.includes(token) || summaryToken.includes(token);
    })
    .map((option) => option.value);
  const requiresTargetChoices = selectedTargetChoices.length > 0 || tags.includes("varmepumper") || targetNameToken.includes("varmepumpe") || summaryToken.includes("varmepumpe");
  const targetChoices = requiresTargetChoices ? HEAT_PUMP_TARGETS : [];
  const standardTasks = requiresRobots
    ? ["Rengjort", "Rengjort brett", "Skiftet mopper", "Skiftet valse"]
    : (requiresTargetChoices ? HEAT_PUMP_STANDARD_TASKS : []);
  const selectedStandardTasks = standardTasksFromLog(row, standardTasks);
  const defaultStandardTasks = selectedStandardTasks.length
    ? selectedStandardTasks
    : (requiresRobots ? ["Rengjort"] : (requiresTargetChoices ? ["Renset filter"] : []));
  return {
    key: `edit-${row.id}`,
    title: summary,
    detail: "Rediger",
    category: "Rediger",
    targetType,
    targetName: safeText(row.target_name),
    actionType,
    priority: safeText(row.priority, "Normal"),
    status: safeText(row.status, "Utført"),
    summary,
    requiresRoom,
    requiresRobots,
    targetChoices,
    targetChoiceLabel: requiresTargetChoices ? "Varmepumper" : "",
    allTargetName: requiresTargetChoices ? "Alle varmepumper" : "",
    standardTasks,
    defaultStandardTasks,
    presenceType: safeText(row.presence_type, "Tilstede Sun2"),
    tags,
    selectedRobots,
    selectedTargetChoices,
    selectedStandardTasks: defaultStandardTasks,
    initialFocus: "summary",
  };
}

function setFormFromLog(row) {
  const task = taskFromLog(row);
  const performedBy = safeText(row.performed_by, currentUsername());
  state.selectedTask = task;
  state.editingLog = row;
  $("#performed_at").value = localDateTimeValue(row.performed_at);
  $("#performed_by").value = performedBy;
  $("#entryUserLine").textContent = `Registrert av ${performedBy} - redigerer egen post`;
  setTimeFieldVisible(false);
  updateTimeButton();
  fillSelect("room_id", optionList("room_id"), safeText(row.room_id), true);
  renderRoomChoices();
  $("#roomField").classList.toggle("is-hidden", !task.requiresRoom);
  state.selectedRobots = [...(task.selectedRobots || [])];
  $("#robotField").classList.toggle("is-hidden", !task.requiresRobots);
  renderRobotChoices();
  state.selectedTargetChoices = [...(task.selectedTargetChoices || [])];
  $("#targetChoiceField").classList.toggle("is-hidden", !targetChoiceOptions(task).length);
  renderTargetChoices();
  state.selectedStandardTasks = [...(task.selectedStandardTasks || task.defaultStandardTasks || [])];
  $("#standardTaskField").classList.toggle("is-hidden", !(task.standardTasks || []).length);
  renderStandardTaskChoices();
  $("#summary").value = task.summary;
  setNoteFieldVisible(true);
  $("#duration_minutes").value = row.duration_minutes === null || row.duration_minutes === undefined ? "" : String(row.duration_minutes);
  $("#follow_up_needed").checked = Boolean(row.follow_up_needed);
  $("#follow_up_text").value = safeText(row.follow_up_text);
  setFollowUpVisible();
  updateSubmitState();
}

function openTask(taskKey) {
  const task = TASKS.find((item) => item.key === taskKey);
  if (!task) return;
  state.selectedTask = task;
  state.editingLog = null;
  const taskCategory = $("#taskCategory");
  if (taskCategory) taskCategory.textContent = task.category || "Oppgave";
  $("#taskTitle").textContent = task.title;
  $("#taskSubtitle").textContent = task.requiresRoom
    ? "Velg seng/rom og lagre posten."
    : (targetChoiceOptions(task).length ? "Velg enhet og oppgave, og lagre posten." : "Fyll eventuelt inn notat og lagre posten.");
  setTaskDefaults(task);
  showScreen("entry");
  renderRecent();
  focusInitialTaskField(task);
}

function openLogForEdit(logId) {
  const row = (state.bootstrap?.recent || []).find((item) => String(item.id) === String(logId));
  if (!row) {
    setTaskMessage("Fant ikke vedlikeholdsposten.", true);
    return;
  }
  if (!isOwnLog(row)) {
    setTaskMessage("Du kan bare redigere egne vedlikeholdsposter.", true);
    return;
  }
  setFormFromLog(row);
  $("#taskTitle").textContent = safeText(row.summary, "Vedlikehold");
  $("#taskSubtitle").textContent = "";
  showScreen("entry");
  renderRecent();
  focusAfterScreenChange("#summary", { select: true, scroll: true });
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
    const editable = isOwnLog(row);
    const tagName = editable ? "button" : "article";
    const actionAttrs = editable ? ` type="button" data-log-id="${row.id}" aria-label="Rediger ${safeText(row.summary, "vedlikeholdspost")}"` : "";
    return `
      <${tagName} class="recent-item ${editable ? "is-editable" : ""}"${actionAttrs}>
        <div class="recent-main">
          <strong>${safeText(row.summary, "Uten notat")}</strong>
          <span class="recent-meta">${safeText(target, "Generelt")}</span>
          <span class="recent-meta">${meta}</span>
          ${row.tags ? `<span class="recent-tags">${safeText(row.tags)}</span>` : ""}
        </div>
        <span class="recent-status ${statusClass}">${row.follow_up_needed ? "Oppfølging" : safeText(row.status, "Utført")}</span>
      </${tagName}>
    `;
  }).join("");
  container.querySelectorAll("[data-log-id]").forEach((button) => {
    button.addEventListener("click", () => openLogForEdit(button.dataset.logId));
  });
}

function updateHeader() {
  const user = safeText(state.bootstrap?.user?.username, "ukjent bruker");
  const role = safeText(state.bootstrap?.user?.roleLabel || state.bootstrap?.user?.role, "innlogget");
  const userLine = $("#userLine");
  if (userLine) userLine.textContent = `${user} - ${role} - lagres i Fibaro10`;
  const topUserInitial = $("#topUserInitial");
  if (topUserInitial) topUserInitial.textContent = user.slice(0, 1).toUpperCase() || "?";
  renderProfile();
}

function renderProfile() {
  const userPayload = state.bootstrap?.user || {};
  const username = safeText(userPayload.username || userPayload.user || userPayload.name, "ukjent bruker");
  const role = safeText(userPayload.roleLabel || userPayload.role, "innlogget");
  const displayName = safeText(userPayload.displayName || userPayload.fullName || userPayload.name);
  const initial = username.slice(0, 1).toUpperCase() || "?";
  const rows = [
    ["Brukernavn", username],
    ["Rolle", role],
    ["Tilgang", "Fibaro10 brukerbase"],
  ];
  if (displayName && normalizeToken(displayName) !== normalizeToken(username)) {
    rows.splice(1, 0, ["Navn", displayName]);
  }

  const profileInitial = $("#profileInitial");
  const profileUserName = $("#profileUserName");
  const profileUserRole = $("#profileUserRole");
  const profileDetails = $("#profileDetails");
  if (profileInitial) profileInitial.textContent = initial;
  if (profileUserName) profileUserName.textContent = displayName || username;
  if (profileUserRole) profileUserRole.textContent = role;
  if (!profileDetails) return;
  profileDetails.innerHTML = "";
  for (const [label, value] of rows) {
    const dt = document.createElement("dt");
    const dd = document.createElement("dd");
    dt.textContent = label;
    dd.textContent = value;
    profileDetails.append(dt, dd);
  }
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
  const robotLabels = selectedRobotLabels();
  const targetChoiceLabels = selectedTargetChoiceLabels(task);
  const standardTaskLabels = selectedStandardTaskLabels();
  const allRobotsSelected = task.requiresRobots && robotLabels.length > 0 && robotLabels.length === optionList("robots").length;
  const allTargetChoicesSelected = targetChoiceOptions(task).length > 0 && targetChoiceLabels.length === targetChoiceOptions(task).length;
  const robotTargetName = allRobotsSelected
    ? `Alle robotvaskere: ${robotLabels.join(", ")}`
    : robotLabels.join(", ");
  const targetChoiceName = allTargetChoicesSelected
    ? `${task.allTargetName || "Alle"}: ${targetChoiceLabels.join(", ")}`
    : targetChoiceLabels.join(", ");
  const currentSummary = safeText($("#summary").value, task.summary || task.title);
  const defaultSummary = safeText(task.summary || task.title);
  const summary = !state.editingLog && (task.requiresRobots || (task.standardTasks || []).length) && currentSummary === defaultSummary
    ? autoSummaryForTask(task, standardTaskLabels, robotLabels, allRobotsSelected, targetChoiceLabels, allTargetChoicesSelected)
    : currentSummary;
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
    target_name: task.requiresRobots
      ? (robotTargetName || task.targetName || "")
      : (targetChoiceName || task.targetName || ""),
    action_type: validOption("action_type", task.actionType || "Kontroll", "Kontroll"),
    priority: validOption("priority", task.priority || "Normal", "Normal"),
    status: validOption("status", statusValue, "Utført"),
    summary,
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
  if (state.selectedTask?.requiresRobots && optionList("robots").length > 0 && state.selectedRobots.length === 0) {
    setMessage("Velg robotvasker før du lagrer.", true);
    updateSubmitState();
    return;
  }
  if (targetChoiceOptions(state.selectedTask).length > 0 && state.selectedTargetChoices.length === 0) {
    setMessage(`Velg ${state.selectedTask?.targetChoiceLabel || "valg"} før du lagrer.`, true);
    updateSubmitState();
    return;
  }
  if ((state.selectedTask?.standardTasks || []).length > 0 && state.selectedStandardTasks.length === 0) {
    setMessage("Velg minst en oppgave før du lagrer.", true);
    updateSubmitState();
    return;
  }
  const editing = Boolean(state.editingLog?.id);
  const savedTitle = state.selectedTask?.title || "Vedlikehold";
  state.busy = true;
  updateSubmitState();
  setMessage("Lagrer...");
  try {
    const response = await fetch(editing ? `/api/maintenance/logs/${encodeURIComponent(state.editingLog.id)}` : "/api/maintenance/logs", {
      method: editing ? "PATCH" : "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(formPayload()),
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.detail || payload.message || "Kunne ikke lagre.");
    state.lastSavedTitle = savedTitle;
    state.selectedTask = null;
    state.editingLog = null;
    await loadBootstrap();
    showScreen("tasks");
    setTaskMessage(`${editing ? "Endret" : "Lagret"}: ${savedTitle}`);
  } catch (error) {
    setMessage(error.message || String(error), true);
  } finally {
    state.busy = false;
    updateSubmitState();
  }
}

document.addEventListener("DOMContentLoaded", async () => {
  $("#maintenanceForm")?.addEventListener("submit", submitForm);
  $("#profileButton")?.addEventListener("click", () => {
    renderProfile();
    showScreen("profile");
  });
  $("#profileBackButton")?.addEventListener("click", () => showScreen("tasks"));
  $("#backButton")?.addEventListener("click", () => {
    state.selectedTask = null;
    state.editingLog = null;
    state.selectedRobots = [];
    state.selectedTargetChoices = [];
    state.selectedStandardTasks = [];
    showScreen("tasks");
    renderRecent();
  });
  $("#follow_up_needed")?.addEventListener("change", setFollowUpVisible);
  $("#room_id")?.addEventListener("change", () => {
    renderRoomChoices();
    updateSubmitState();
  });
  $("#robotAllButton")?.addEventListener("click", toggleAllRobots);
  $("#targetChoiceAllButton")?.addEventListener("click", toggleAllTargetChoices);
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
