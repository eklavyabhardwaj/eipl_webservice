// Apple-like product gallery: drag/scroll + dots + thumbs sync
document.addEventListener("DOMContentLoaded", () => {
  const galleries = document.querySelectorAll("[data-gallery]");

  galleries.forEach((root) => {
    const track = root.querySelector("[data-gallery-track]");
    const slides = Array.from(root.querySelectorAll("[data-gallery-slide]"));
    const dots  = Array.from(root.querySelectorAll("[data-gallery-dot]"));
    const thumbs= Array.from(root.querySelectorAll("[data-gallery-thumb]"));

    // Basic drag-to-scroll
    let isDown = false, startX = 0, scrollLeft = 0;
    const start = (x) => { isDown = true; startX = x; scrollLeft = track.scrollLeft; track.classList.add("dragging"); };
    const move  = (x) => { if(!isDown) return; track.scrollLeft = scrollLeft - (x - startX); };
    const end   = ()   => { isDown = false; track.classList.remove("dragging"); };

    track.addEventListener("mousedown", (e)=>start(e.pageX));
    window.addEventListener("mousemove", (e)=>move(e.pageX));
    window.addEventListener("mouseup", end);
    track.addEventListener("mouseleave", end);

    track.addEventListener("touchstart",(e)=>start(e.touches[0].pageX), {passive:true});
    track.addEventListener("touchmove",(e)=>move(e.touches[0].pageX), {passive:true});
    track.addEventListener("touchend", end);

    // Observe which slide is centered to update dots/thumbs
    const io = new IntersectionObserver((entries)=>{
      entries.forEach((entry)=>{
        if(entry.isIntersecting){
          const idx = slides.indexOf(entry.target);
          dots.forEach((d,i)=>d.setAttribute("aria-current", i===idx ? "true":"false"));
          thumbs.forEach((t,i)=>t.setAttribute("aria-current", i===idx ? "true":"false"));
        }
      });
    }, { root: track, threshold: 0.6 });



    slides.forEach(slide => io.observe(slide));

    // Controls
    const scrollToIndex = (i) => {
      const el = slides[i];
      if(!el) return;
      track.scrollTo({ left: el.offsetLeft, behavior: "smooth" });
    };

    dots.forEach((dot,i)=>dot.addEventListener("click", ()=>scrollToIndex(i)));
    thumbs.forEach((th,i)=>th.addEventListener("click", ()=>scrollToIndex(i)));
  });
});
