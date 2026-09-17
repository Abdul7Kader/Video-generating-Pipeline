(() => {
  "use strict";

  const storageKey = "video-pipeline-theme";
  const root = document.documentElement;
  const systemPreference = window.matchMedia("(prefers-color-scheme: dark)");

  function storedTheme() {
    try {
      const value = localStorage.getItem(storageKey);
      return value === "dark" || value === "light" ? value : null;
    } catch {
      return null;
    }
  }

  function preferredTheme() {
    return storedTheme() || (systemPreference.matches ? "dark" : "light");
  }

  function updateToggle(theme) {
    const toggle = document.getElementById("theme-toggle");
    if (!toggle) return;

    const dark = theme === "dark";
    const label = dark ? "Hellen Modus aktivieren" : "Dunklen Modus aktivieren";
    toggle.setAttribute("aria-pressed", String(dark));
    toggle.setAttribute("aria-label", label);
    toggle.title = label;
    toggle.querySelector(".theme-icon").textContent = dark ? "☀" : "☾";
    toggle.querySelector(".theme-label").textContent = dark ? "Hell" : "Dunkel";
  }

  function applyTheme(theme) {
    root.dataset.theme = theme;
    root.style.colorScheme = theme;
    updateToggle(theme);
  }

  applyTheme(preferredTheme());

  document.addEventListener("DOMContentLoaded", () => {
    applyTheme(preferredTheme());

    document.getElementById("theme-toggle")?.addEventListener("click", () => {
      const nextTheme = root.dataset.theme === "dark" ? "light" : "dark";
      try {
        localStorage.setItem(storageKey, nextTheme);
      } catch {
        // The theme remains active for this session when storage is unavailable.
      }
      applyTheme(nextTheme);
    });
  });

  systemPreference.addEventListener("change", (event) => {
    if (!storedTheme()) applyTheme(event.matches ? "dark" : "light");
  });
})();
