// static/menu.js
document.addEventListener("DOMContentLoaded", () => {
  const wraps = document.querySelectorAll(".nav__item--hasmega");

  const setExpanded = (el, expanded) => {
    el.setAttribute("aria-expanded", String(expanded));
    const btn = el.querySelector(".nav__btn");
    if (btn) btn.setAttribute("aria-expanded", String(expanded));
  };

  wraps.forEach((wrap) => {
    const btn = wrap.querySelector(".nav__btn");
    const panel = wrap.querySelector(".mega");
    if (!btn || !panel) return;

    // init ARIA
    setExpanded(wrap, false);

    // click toggle (also closes other open menus)
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      const open = wrap.getAttribute("aria-expanded") !== "true";
      document
        .querySelectorAll('.nav__item--hasmega[aria-expanded="true"]')
        .forEach((o) => setExpanded(o, false));
      setExpanded(wrap, open);
    });

    // hover intent (desktop)
    let hoverTimer;
    wrap.addEventListener("mouseenter", () => {
      clearTimeout(hoverTimer);
      setExpanded(wrap, true);
    });
    wrap.addEventListener("mouseleave", () => {
      hoverTimer = setTimeout(() => setExpanded(wrap, false), 120);
    });
  });

  // click-away close
  document.addEventListener("click", (e) => {
    const openWrap = document.querySelector(
      '.nav__item--hasmega[aria-expanded="true"]'
    );
    if (!openWrap) return;
    if (!openWrap.contains(e.target)) setExpanded(openWrap, false);
  });

  // esc to close
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      document
        .querySelectorAll('.nav__item--hasmega[aria-expanded="true"]')
        .forEach((o) => setExpanded(o, false));
    }
  });
});
