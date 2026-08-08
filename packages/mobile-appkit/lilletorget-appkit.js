(() => {
  const storageKey = "lilletorget-mobile-theme";
  const root = document.documentElement;
  const body = document.body;

  const preferredTheme = () => {
    const stored = window.localStorage.getItem(storageKey);
    if (stored === "light" || stored === "dark") return stored;
    return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  };

  const applyTheme = (theme, persist = false) => {
    const dark = theme === "dark";
    const actionLabel = dark ? "Bytt til lyst tema" : "Bytt til m\u00f8rkt tema";
    root.dataset.theme = dark ? "dark" : "light";
    body.classList.remove("theme-dark", "theme-light");
    body.classList.toggle("appkit-theme-dark", dark);
    body.classList.toggle("appkit-theme-light", !dark);
    document.querySelector('meta[name="theme-color"]')?.setAttribute(
      "content",
      dark ? "#15191f" : "#ffffff",
    );
    document.querySelectorAll("[data-theme-label]").forEach((node) => {
      node.textContent = dark ? "Lyst tema" : "M\u00f8rkt tema";
    });
    document.querySelectorAll("[data-toggle-theme]").forEach((node) => {
      node.setAttribute("aria-label", actionLabel);
      node.setAttribute("title", actionLabel);
    });
    if (persist) window.localStorage.setItem(storageKey, dark ? "dark" : "light");
  };

  applyTheme(preferredTheme());

  document.addEventListener("click", (event) => {
    const toggle = event.target.closest("[data-toggle-theme]");
    if (toggle) {
      event.preventDefault();
      applyTheme(root.dataset.theme === "dark" ? "light" : "dark", true);
      return;
    }

    const back = event.target.closest("[data-back-button]");
    if (back) {
      event.preventDefault();
      if (window.history.length > 1) window.history.back();
      else window.location.assign(back.getAttribute("href") || "/");
    }
  });

  window.matchMedia?.("(prefers-color-scheme: dark)").addEventListener?.("change", (event) => {
    if (!window.localStorage.getItem(storageKey)) applyTheme(event.matches ? "dark" : "light");
  });

  window.addEventListener("load", () => {
    document.getElementById("preloader")?.classList.add("is-complete");
  });
})();
