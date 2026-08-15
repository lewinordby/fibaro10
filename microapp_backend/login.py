from __future__ import annotations

from html import escape

from .pwa import PwaConfig, pwa_head_tags


LOGIN_PAGE_TEMPLATE = """<!doctype html>
<html lang="no" data-theme="light">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="color-scheme" content="light dark">
<title>Logg inn - __APP_NAME__</title>
__PWA_TAGS__
<script nonce="__CSP_NONCE__">
(() => {
  try {
    const stored = window.localStorage.getItem("theme");
    const dark = stored === "dark" || (!stored && window.matchMedia("(prefers-color-scheme: dark)").matches);
    document.documentElement.dataset.theme = dark ? "dark" : "light";
  } catch (_) {}
})();
</script>
<style>
:root {
  color-scheme: light;
  --auth-bg: #f3f6fa;
  --auth-surface: #ffffff;
  --auth-surface-soft: #f8fafc;
  --auth-line: #d7e0ea;
  --auth-line-strong: #b9c6d5;
  --auth-text: #071b44;
  --auth-muted: #66738a;
  --auth-navy: #071b44;
  --auth-navy-hover: #102b61;
  --auth-gold: #d99a16;
  --auth-error: #a3312a;
  --auth-error-bg: #fff2f0;
  --auth-error-line: #f0c5c0;
  --auth-shadow: 0 20px 55px rgba(7, 27, 68, 0.12);
}
html[data-theme="dark"] {
  color-scheme: dark;
  --auth-bg: #0c131d;
  --auth-surface: #141e2a;
  --auth-surface-soft: #182431;
  --auth-line: #2c3a49;
  --auth-line-strong: #425164;
  --auth-text: #f2f6fb;
  --auth-muted: #a8b5c5;
  --auth-navy: #e6a72a;
  --auth-navy-hover: #f0b73f;
  --auth-error: #ffb8b2;
  --auth-error-bg: #321c20;
  --auth-error-line: #6f3338;
  --auth-shadow: 0 24px 60px rgba(0, 0, 0, 0.34);
}
* { box-sizing: border-box; }
html, body { min-height: 100%; }
body {
  margin: 0;
  background: var(--auth-bg);
  color: var(--auth-text);
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  font-size: 16px;
  line-height: 1.5;
  letter-spacing: 0;
  -webkit-font-smoothing: antialiased;
}
button, input { font: inherit; letter-spacing: 0; }
.auth-layout {
  min-height: 100dvh;
  display: grid;
  grid-template-columns: minmax(23rem, 0.82fr) minmax(31rem, 1.18fr);
}
.brand-stage {
  position: relative;
  min-height: 100dvh;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  overflow: hidden;
  padding: clamp(2rem, 5vw, 4.5rem);
  border-right: 4px solid var(--auth-gold);
  background: #071b44;
  color: #ffffff;
}
.brand-stage::after {
  content: "";
  position: absolute;
  inset: auto 0 0;
  height: 6px;
  background: #d99a16;
}
.brand-lockup {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 1rem;
}
.brand-mark {
  width: 4.4rem;
  height: 4.4rem;
  flex: 0 0 4.4rem;
}
.brand-mark .mark-sun { stroke: #e6a72a; }
.brand-mark .mark-p { stroke: #ffffff; }
.brand-name {
  margin: 0;
  font-size: 2rem;
  font-weight: 650;
  line-height: 1;
}
.brand-caption {
  margin: 0.42rem 0 0;
  color: #b8c7dc;
  font-size: 0.82rem;
  font-weight: 650;
}
.brand-message {
  position: relative;
  z-index: 1;
  max-width: 33rem;
  padding: 4rem 0;
}
.brand-eyebrow {
  margin: 0 0 1rem;
  color: #e6a72a;
  font-size: 0.86rem;
  font-weight: 750;
}
.brand-message h1 {
  max-width: 30rem;
  margin: 0;
  color: #ffffff;
  font-size: 3.25rem;
  font-weight: 680;
  line-height: 1.08;
}
.brand-message p {
  max-width: 29rem;
  margin: 1.25rem 0 0;
  color: #c1cee0;
  font-size: 1.06rem;
}
.brand-context {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: 1fr auto;
  align-items: end;
  gap: 1rem;
  padding-top: 1.25rem;
  border-top: 1px solid rgba(255, 255, 255, 0.18);
}
.context-label {
  display: block;
  margin-bottom: 0.25rem;
  color: #9fb0c7;
  font-size: 0.78rem;
}
.context-app {
  display: block;
  color: #ffffff;
  font-size: 1.15rem;
  font-weight: 700;
}
.accent-track {
  display: grid;
  grid-template-columns: repeat(4, 1.7rem);
  gap: 0.35rem;
}
.accent-track span { height: 0.3rem; border-radius: 2px; }
.accent-track span:nth-child(1) { background: #e15759; }
.accent-track span:nth-child(2) { background: #4f72e8; }
.accent-track span:nth-child(3) { background: #e6a72a; }
.accent-track span:nth-child(4) { background: #39a86b; }
.auth-main {
  min-width: 0;
  display: grid;
  place-items: center;
  padding: clamp(1.25rem, 5vw, 4.5rem);
  background: var(--auth-bg);
}
.login-wrap { width: min(100%, 28rem); }
.mobile-brand { display: none; }
.login-card {
  border: 1px solid var(--auth-line);
  border-radius: 8px;
  background: var(--auth-surface);
  box-shadow: var(--auth-shadow);
  padding: 2.25rem;
}
.login-kicker {
  margin: 0 0 0.45rem;
  color: var(--auth-muted);
  font-size: 0.82rem;
  font-weight: 700;
}
.login-card h2 {
  margin: 0;
  color: var(--auth-text);
  font-size: 2rem;
  font-weight: 700;
  line-height: 1.15;
}
.login-subtitle {
  margin: 0.7rem 0 1.65rem;
  color: var(--auth-muted);
  font-size: 0.95rem;
}
.error-message {
  display: flex;
  align-items: flex-start;
  gap: 0.65rem;
  margin: 0 0 1.15rem;
  padding: 0.8rem 0.9rem;
  border: 1px solid var(--auth-error-line);
  border-radius: 8px;
  background: var(--auth-error-bg);
  color: var(--auth-error);
  font-size: 0.9rem;
  font-weight: 650;
}
.error-message svg { width: 1.1rem; height: 1.1rem; flex: 0 0 1.1rem; margin-top: 0.12rem; }
.login-form { display: grid; gap: 1rem; }
.field { display: grid; gap: 0.45rem; }
.field label {
  color: var(--auth-text);
  font-size: 0.84rem;
  font-weight: 700;
}
.input-shell { position: relative; }
.input-icon {
  position: absolute;
  top: 50%;
  left: 0.9rem;
  width: 1.15rem;
  height: 1.15rem;
  transform: translateY(-50%);
  color: var(--auth-muted);
  pointer-events: none;
}
.input-shell input {
  width: 100%;
  height: 3.2rem;
  border: 1px solid var(--auth-line-strong);
  border-radius: 8px;
  outline: none;
  background: var(--auth-surface-soft);
  color: var(--auth-text);
  padding: 0 3rem 0 2.75rem;
  transition: border-color 150ms ease, box-shadow 150ms ease, background 150ms ease;
}
.input-shell input::placeholder { color: var(--auth-muted); opacity: 0.72; }
.input-shell input:hover { border-color: var(--auth-muted); }
.input-shell input:focus {
  border-color: var(--auth-gold);
  background: var(--auth-surface);
  box-shadow: 0 0 0 3px rgba(217, 154, 22, 0.18);
}
.password-toggle {
  position: absolute;
  top: 50%;
  right: 0.55rem;
  width: 2.1rem;
  height: 2.1rem;
  display: grid;
  place-items: center;
  transform: translateY(-50%);
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: var(--auth-muted);
  cursor: pointer;
}
.password-toggle:hover { background: var(--auth-line); color: var(--auth-text); }
.password-toggle:focus-visible { outline: 2px solid var(--auth-gold); outline-offset: 1px; }
.password-toggle svg { width: 1.15rem; height: 1.15rem; }
.password-toggle .eye-off { display: none; }
.password-toggle[aria-pressed="true"] .eye { display: none; }
.password-toggle[aria-pressed="true"] .eye-off { display: block; }
.submit-button {
  width: 100%;
  height: 3.25rem;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.65rem;
  margin-top: 0.35rem;
  border: 1px solid var(--auth-navy);
  border-radius: 8px;
  background: var(--auth-navy);
  color: #ffffff;
  font-weight: 750;
  cursor: pointer;
  box-shadow: 0 10px 24px rgba(7, 27, 68, 0.18);
  transition: background 150ms ease, transform 150ms ease, box-shadow 150ms ease;
}
html[data-theme="dark"] .submit-button { color: #071b44; }
.submit-button:hover {
  background: var(--auth-navy-hover);
  transform: translateY(-1px);
  box-shadow: 0 13px 28px rgba(7, 27, 68, 0.22);
}
.submit-button:active { transform: translateY(0); }
.submit-button:focus-visible { outline: 3px solid rgba(217, 154, 22, 0.35); outline-offset: 2px; }
.submit-button svg { width: 1.1rem; height: 1.1rem; }
.login-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin: 1rem 0 0;
  color: var(--auth-muted);
  font-size: 0.76rem;
}
.secure-label { display: inline-flex; align-items: center; gap: 0.4rem; }
.secure-label svg { width: 0.9rem; height: 0.9rem; }
@media (max-width: 860px) {
  .auth-layout { grid-template-columns: 1fr; }
  .brand-stage {
    min-height: auto;
    padding: calc(1rem + env(safe-area-inset-top)) 1.25rem 1rem;
    border-right: 0;
    border-bottom: 3px solid var(--auth-gold);
  }
  .brand-stage::after, .brand-message, .brand-context { display: none; }
  .brand-lockup { gap: 0.7rem; }
  .brand-mark { width: 2.8rem; height: 2.8rem; flex-basis: 2.8rem; }
  .brand-name { font-size: 1.35rem; }
  .brand-caption { margin-top: 0.2rem; font-size: 0.72rem; }
  .auth-main {
    place-items: start center;
    min-height: calc(100dvh - 5.1rem);
    padding: 1.25rem 1rem calc(1.5rem + env(safe-area-inset-bottom));
  }
  .login-card { padding: 1.4rem; }
  .login-card h2 { font-size: 1.65rem; }
}
@media (max-width: 420px) {
  .login-wrap { width: 100%; }
  .login-card { border-radius: 8px; padding: 1.25rem; }
  .login-meta { align-items: flex-start; flex-direction: column; gap: 0.3rem; }
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { scroll-behavior: auto !important; transition-duration: 0.01ms !important; }
}
</style>
</head>
<body>
<main class="auth-layout">
  <section class="brand-stage" aria-label="Lilletorget">
    <div class="brand-lockup">
      <svg class="brand-mark" viewBox="0 0 128 128" role="img" aria-label="Lilletorget-symbol">
        <g class="mark-sun" fill="none" stroke-width="5.5" stroke-linecap="round">
          <circle cx="64" cy="64" r="34"></circle>
          <path d="M64 6v12M64 110v12M6 64h12M110 64h12M22.99 22.99l8.49 8.49M96.52 96.52l8.49 8.49M22.99 105.01l8.49-8.49M96.52 31.48l8.49-8.49"></path>
        </g>
        <path class="mark-p" d="M49 101V38h17c13 0 21 7.5 21 19s-8 19-21 19H49" fill="none" stroke-width="8.5" stroke-linecap="square" stroke-linejoin="round"></path>
      </svg>
      <div>
        <p class="brand-name">Lilletorget</p>
        <p class="brand-caption">Soling · parkering · drift</p>
      </div>
    </div>
    <div class="brand-message">
      <p class="brand-eyebrow">Operativ plattform</p>
      <h1>Alt samlet.<br>Ett sikkert sted.</h1>
      <p>Én inngang til den daglige oversikten og verktøyene som holder Lilletorget i gang.</p>
    </div>
    <div class="brand-context">
      <div>
        <span class="context-label">Du logger inn til</span>
        <strong class="context-app">__APP_NAME__</strong>
      </div>
      <div class="accent-track" aria-hidden="true"><span></span><span></span><span></span><span></span></div>
    </div>
  </section>
  <section class="auth-main">
    <div class="login-wrap">
      <div class="login-card">
        <header>
          <p class="login-kicker">Lilletorget · __APP_NAME__</p>
          <h2>Logg inn</h2>
          <p class="login-subtitle">Én innlogging gjelder i alle Lilletorget-appene.</p>
        </header>
        __ERROR_HTML__
        <form class="login-form" method="post" action="/auth/login">
          <div class="field">
            <label for="username">Brukernavn</label>
            <div class="input-shell">
              <svg class="input-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M20 21a8 8 0 0 0-16 0"></path><circle cx="12" cy="7" r="4"></circle></svg>
              <input id="username" name="username" type="text" placeholder="Skriv brukernavn" autocomplete="username" autocapitalize="none" spellcheck="false" autofocus required>
            </div>
          </div>
          <div class="field">
            <label for="password">Passord</label>
            <div class="input-shell">
              <svg class="input-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><rect width="18" height="11" x="3" y="11" rx="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>
              <input id="password" name="password" type="password" placeholder="Skriv passord" autocomplete="current-password" required>
              <button class="password-toggle" type="button" aria-label="Vis passord" aria-pressed="false" title="Vis eller skjul passord">
                <svg class="eye" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M2.06 12.35a1 1 0 0 1 0-.7C3.7 7.6 7.56 5 12 5c4.44 0 8.3 2.6 9.94 6.65a1 1 0 0 1 0 .7C20.3 16.4 16.44 19 12 19c-4.44 0-8.3-2.6-9.94-6.65Z"></path><circle cx="12" cy="12" r="3"></circle></svg>
                <svg class="eye-off" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="m2 2 20 20"></path><path d="M6.71 6.71C4.96 7.93 3.55 9.64 2.85 11.65a1 1 0 0 0 0 .7C4.5 16.4 8.35 19 12.79 19c1.32 0 2.58-.23 3.73-.65"></path><path d="M10.73 5.08A9.8 9.8 0 0 1 12.79 5c4.44 0 8.3 2.6 9.94 6.65a1 1 0 0 1 0 .7 10.4 10.4 0 0 1-1.1 2.1"></path><path d="M14.9 14.9A4 4 0 0 1 9.1 9.1"></path></svg>
              </button>
            </div>
          </div>
          <button class="submit-button" type="submit">
            <span>Logg inn</span>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M5 12h14"></path><path d="m13 6 6 6-6 6"></path></svg>
          </button>
        </form>
      </div>
      <div class="login-meta">
        <span class="secure-label"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M20 13c0 5-3.5 7.5-8 9-4.5-1.5-8-4-8-9V5l8-3 8 3Z"></path><path d="m9 12 2 2 4-4"></path></svg>Sikker intern tilgang</span>
        <span>Build __BUILD__</span>
      </div>
    </div>
  </section>
</main>
<script nonce="__CSP_NONCE__">
(() => {
  const button = document.querySelector(".password-toggle");
  const input = document.querySelector("#password");
  if (!button || !input) return;
  button.addEventListener("click", () => {
    const visible = input.type === "text";
    input.type = visible ? "password" : "text";
    button.setAttribute("aria-pressed", visible ? "false" : "true");
    button.setAttribute("aria-label", visible ? "Vis passord" : "Skjul passord");
    input.focus();
  });
})();
</script>
</body>
</html>
"""


def render_login_page(*, app_name: str, build: str, pwa: PwaConfig, error: str = "", nonce: str = "") -> str:
    safe_error = escape(error.strip())
    error_html = ""
    if safe_error:
        error_html = (
            '<div class="error-message" role="alert" aria-live="polite">'
            '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">'
            '<circle cx="12" cy="12" r="10"></circle><path d="M12 8v4"></path><path d="M12 16h.01"></path>'
            f"</svg><span>{safe_error}</span></div>"
        )
    return (
        LOGIN_PAGE_TEMPLATE.replace("__APP_NAME__", escape(app_name))
        .replace("__BUILD__", escape(str(build)))
        .replace("__PWA_TAGS__", pwa_head_tags(pwa))
        .replace("__ERROR_HTML__", error_html)
        .replace("__CSP_NONCE__", escape(nonce))
    )
