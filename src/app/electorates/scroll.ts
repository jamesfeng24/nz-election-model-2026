/** Long enough to outlast a seat folding shut above the target (see Collapsible), so the target has settled. */
const DURATION_MS = 450;
const GAP_PX = 12;

const reducedMotion = () => window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false;

/**
 * Scrolls so the element sits just below the top of the window: a short ease-out glide, not a snap. The target is
 * read again on every frame, because a seat folding shut above it moves it while the page glides.
 */
export function glideTo(element: HTMLElement | null) {
  if (!element) return;
  const start = window.scrollY;
  const targetAt = () => Math.max(0, window.scrollY + element.getBoundingClientRect().top - GAP_PX);
  if (reducedMotion() || typeof window.requestAnimationFrame !== 'function') {
    window.scrollTo(0, targetAt());
    return;
  }
  const began = performance.now();
  const step = (now: number) => {
    const t = Math.min(1, (now - began) / DURATION_MS);
    const eased = 1 - (1 - t) ** 3;
    const end = targetAt();
    window.scrollTo(0, start + (end - start) * eased);
    if (t < 1) window.requestAnimationFrame(step);
  };
  window.requestAnimationFrame(step);
}
