(() => {
  const read = (key) => { try { return sessionStorage.getItem(key); } catch { return null; } };
  const write = (key, value) => { try { sessionStorage.setItem(key, value); } catch { /* Storage is optional. */ } };
  const dashboard = document.querySelector('.revenue-dashboard');
  if (dashboard) {
    const tabs = [...dashboard.querySelectorAll('[data-period-tab]')];
    const panels = [...dashboard.querySelectorAll('[data-period]')];
    const select = (key, focus = false) => {
      if (!tabs.some(tab => tab.dataset.periodTab === key)) key = 'today';
      for (const tab of tabs) {
        const active = tab.dataset.periodTab === key;
        tab.setAttribute('aria-selected', String(active));
        tab.tabIndex = active ? 0 : -1;
        if (active && focus) tab.focus();
      }
      for (const panel of panels) {
        panel.hidden = panel.dataset.period !== key;
        panel.setAttribute('role', 'tabpanel');
        panel.setAttribute('aria-labelledby', `revenue-tab-${panel.dataset.period}`);
        panel.tabIndex = 0;
      }
      write('mobile-revenue-period', key);
    };
    select(read('mobile-revenue-period'));
    dashboard.querySelector('.rev-period-tabs').hidden = false;
    tabs.forEach((tab, index) => {
      tab.addEventListener('click', () => select(tab.dataset.periodTab));
      tab.addEventListener('keydown', event => {
        let next;
        if (event.key === 'ArrowRight') next = (index + 1) % tabs.length;
        if (event.key === 'ArrowLeft') next = (index + tabs.length - 1) % tabs.length;
        if (event.key === 'Home') next = 0;
        if (event.key === 'End') next = tabs.length - 1;
        if (next === undefined) return;
        event.preventDefault();
        select(tabs[next].dataset.periodTab, true);
      });
    });
  }
  document.querySelectorAll('details[data-state-key]').forEach(detail => {
    const key = `mobile-detail:${location.pathname}:${detail.dataset.stateKey}`;
    detail.open = read(key) === 'open';
    const persist = () => write(key, detail.open ? 'open' : 'closed');
    detail.addEventListener('toggle', persist);
    window.addEventListener('pagehide', persist);
  });
})();
