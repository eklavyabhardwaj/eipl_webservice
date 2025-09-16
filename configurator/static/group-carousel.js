// Group carousel: arrows show when overflow or >3 cells; drag-to-swipe; snap-aware buttons
document.addEventListener("DOMContentLoaded", () => {
  const carousels = Array.from(document.querySelectorAll("[data-carousel]"));
  if (!carousels.length) return;

  const clamp = (v, min, max) => Math.max(min, Math.min(max, v));

  carousels.forEach((wrap) => {
    const track = wrap.querySelector("[data-track]");
    const prevBtn = wrap.querySelector(".carousel-btn--prev");
    const nextBtn = wrap.querySelector(".carousel-btn--next");
    if (!track || !prevBtn || !nextBtn) return;

    const cells = Array.from(track.children);
    const showArrows = () => {
      const hasOverflow = track.scrollWidth > track.clientWidth + 4; // tolerance
      const manyCells = cells.length > 3;
      const shouldShow = hasOverflow || manyCells;
      prevBtn.hidden = nextBtn.hidden = !shouldShow;
      updateDisabled();
    };

    const snapAmount = () => {
      // Scroll by one cell width + gap (approx)
      const firstCell = cells[0];
      if (!firstCell) return track.clientWidth * 0.8;
      const style = window.getComputedStyle(track);
      const gap = parseFloat(style.columnGap || style.gap || 16);
      return firstCell.getBoundingClientRect().width + gap;
    };

    const scrollByAmount = (dir) => {
      track.scrollBy({ left: dir * snapAmount(), behavior: "smooth" });
    };

    const updateDisabled = () => {
      // Disable prev at left edge, next at right edge
      const maxScroll = track.scrollWidth - track.clientWidth - 1;
      prevBtn.disabled = track.scrollLeft <= 0;
      nextBtn.disabled = track.scrollLeft >= maxScroll;
    };

    // Buttons
    prevBtn.addEventListener("click", () => scrollByAmount(-1));
    nextBtn.addEventListener("click", () => scrollByAmount(1));

    // Drag to scroll
    let isDown = false;
    let startX = 0;
    let startLeft = 0;
    let moved = false;

    const onDown = (e) => {
      isDown = true;
      moved = false;
      startX = (e.touches ? e.touches[0].clientX : e.clientX);
      startLeft = track.scrollLeft;
      track.classList.add("is-dragging");
    };
    const onMove = (e) => {
      if (!isDown) return;
      const x = (e.touches ? e.touches[0].clientX : e.clientX);
      const dx = x - startX;
      if (Math.abs(dx) > 3) moved = true;
      track.scrollLeft = startLeft - dx;
    };
    const onUp = (e) => {
      if (!isDown) return;
      isDown = false;
      track.classList.remove("is-dragging");
      // If user dragged, prevent click-through on child links
      if (moved) {
        const suppress = (ev) => { ev.stopPropagation(); ev.preventDefault(); };
        track.addEventListener("click", suppress, true);
        setTimeout(() => track.removeEventListener("click", suppress, true), 0);
      }
    };

    track.addEventListener("mousedown", onDown);
    track.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    track.addEventListener("touchstart", onDown, { passive: true });
    track.addEventListener("touchmove", onMove, { passive: true });
    track.addEventListener("touchend", onUp);

    // Keep buttons state in sync
    const onScroll = () => updateDisabled();
    const onResize = () => showArrows();
    track.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onResize);

    // Init
    showArrows();
    updateDisabled();
  });
});
