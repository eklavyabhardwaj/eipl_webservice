// modal.js — hardened modal controls that defeat history.back() hijacks
(function () {
  const modal = document.getElementById("contactModal");
  if (!modal) return;

  const dialog = modal.querySelector(".modal__dialog") || modal;
  const openers = Array.from(document.querySelectorAll("[data-open-contact]"));

  let lastFocused = null;
  const isOpen = () => getComputedStyle(modal).display !== "none";

  function getFocusable() {
    return Array.from(modal.querySelectorAll(
      "a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex='-1'])"
    )).filter(el => el.offsetParent !== null || el === document.activeElement);
  }

  function show() {
    // prevent duplicate opens
    if (isOpen()) return;

    lastFocused = document.activeElement;
    modal.style.display = "block";
    modal.setAttribute("aria-hidden", "false");
    document.documentElement.style.overflow = "hidden";

    const first = getFocusable()[0];
    if (first) setTimeout(() => first.focus(), 30);
  }

  function hide() {
    if (!isOpen()) return;

    modal.style.display = "none";
    modal.setAttribute("aria-hidden", "true");
    document.documentElement.style.overflow = "";

    // restore focus
    if (lastFocused && typeof lastFocused.focus === "function") {
      setTimeout(() => lastFocused.focus(), 30);
    }
  }

  // Openers: ensure they don't submit forms
  openers.forEach(btn => {
    if (btn.tagName === "BUTTON" && !btn.hasAttribute("type")) btn.setAttribute("type", "button");
    btn.addEventListener("click", (e) => { e.preventDefault(); show(); });
  });

  // Prevent clicks inside dialog from bubbling to modal/document
  dialog.addEventListener("click", e => e.stopPropagation());

  // --- GLOBAL CAPTURE GUARDS (win over any other script) ---
  // Close on ✕ or backdrop (capture + immediate stop)
  document.addEventListener("click", (e) => {
    if (!isOpen()) return;
    const target = e.target;
    const isCloser = target.matches("[data-close-modal]") || target.classList.contains("modal__backdrop");
    if (isCloser) {
      e.preventDefault();
      e.stopPropagation();
      e.stopImmediatePropagation();
      hide();
    }
  }, true); // CAPTURE!

  // Close on Esc (capture + immediate stop)
  document.addEventListener("keydown", (e) => {
    if (!isOpen()) return;
    if (e.key === "Escape") {
      e.preventDefault();
      e.stopPropagation();
      e.stopImmediatePropagation();
      hide();
    }
    // Basic focus trap
    if (e.key === "Tab") {
      const nodes = getFocusable();
      if (!nodes.length) { e.preventDefault(); return; }
      const first = nodes[0], last = nodes[nodes.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault(); last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault(); first.focus();
      }
    }
  }, true); // CAPTURE!

  // Defensive: ensure explicit closers inside the modal are type="button"
  modal.querySelectorAll("[data-close-modal]").forEach(el => {
    if (el.tagName === "BUTTON" && !el.hasAttribute("type")) el.setAttribute("type", "button");
  });

  // Normalize initial state
  if (getComputedStyle(modal).display !== "none") {
    modal.style.display = "none";
    modal.setAttribute("aria-hidden", "true");
  }
})();


document.addEventListener('DOMContentLoaded', () => {
  const openBtn = document.querySelector('[data-open-contact]');
  const modal = document.getElementById('contactModal');
  const closeBtns = modal?.querySelectorAll('[data-close-modal]');

  if (openBtn && modal) {
    openBtn.addEventListener('click', () => {
      modal.setAttribute('open', '');
      modal.style.display = 'flex';
    });

    closeBtns?.forEach(btn => {
      btn.addEventListener('click', () => {
        modal.removeAttribute('open');
        modal.style.display = 'none';
      });
    });
  }
});
