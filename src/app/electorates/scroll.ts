const DURATION_MS = 380;
const GAP_PX = 12;

const reducedMotion = () => window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false;

/** Scrolls so the element sits just below the top of the window: a short ease-out glide, not a snap. */
export function glideTo(element: HTMLElement | null) {
  if (!element) return;
  const start = window.scrollY;
  const end = Math.max(0, start + element.getBoundingClientRect().top - GAP_PX);
  if (reducedMotion() || typeof window.requestAnimationFrame !== 'function') {
    window.scrollTo(0, end);
    return;
  }
  const began = performance.now();
  const step = (now: number) => {
    const t = Math.min(1, (now - began) / DURATION_MS);
    window.scrollTo(0, start + (end - start) * (1 - (1 - t) ** 3));
    if (t < 1) window.requestAnimationFrame(step);
  };
  window.requestAnimationFrame(step);
}
