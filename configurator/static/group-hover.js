// Expand group card to show inline slider on hover/tap
document.addEventListener("DOMContentLoaded", () => {
  const cards = Array.from(document.querySelectorAll("[data-group-card]"));
  if (!cards.length) return;

  const isTouch = matchMedia("(hover: none), (pointer: coarse)").matches;

  const open = (card) => {
    // close others
    cards.forEach(c => { if (c !== card) c.classList.remove("is-open"); });
    card.classList.add("is-open");
  };
  const close = (card) => card.classList.remove("is-open");

  if (!isTouch) {
    // Desktop: hover opens; leaving the card collapses
    cards.forEach(card => {
      card.addEventListener("mouseenter", () => open(card));
      card.addEventListener("mouseleave", () => close(card));
      // keyboard
      card.addEventListener("focusin", () => open(card));
      card.addEventListener("focusout", (e) => {
        if (!card.contains(e.relatedTarget)) close(card);
      });
    });
  } else {
    // Touch: tap toggles; second tap on Start navigates
    cards.forEach(card => {
      card.addEventListener("click", (e) => {
        const startBtn = e.target.closest(".group-card__start");
        if (startBtn) return; // allow navigation

        // first tap opens, second tap outside closes
        if (!card.classList.contains("is-open")) {
          e.preventDefault();
          open(card);
          const onDocTap = (ev) => {
            if (!card.contains(ev.target)) {
              close(card);
              document.removeEventListener("click", onDocTap, true);
            }
          };
          setTimeout(() => document.addEventListener("click", onDocTap, true), 0);
        }
      }, {passive:false});
    });
  }
});
