import { useEffect, useRef, useState, type ReactNode } from 'react';

const DURATION_MS = 300;

const reducedMotion = () =>
  typeof window.matchMedia === 'function' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

/**
 * Opens from nothing to its full height when it appears and closes the same way. `onClosed` runs once the closing
 * has finished, so the caller can drop the content then.
 */
export function Collapsible({
  open,
  onClosed,
  children,
}: {
  open: boolean;
  onClosed?: () => void;
  children: ReactNode;
}) {
  const [entered, setEntered] = useState(false);
  const onClosedRef = useRef(onClosed);
  onClosedRef.current = onClosed;

  useEffect(() => {
    if (!open) return;
    if (reducedMotion()) return setEntered(true);
    const frame = requestAnimationFrame(() => setEntered(true));
    return () => cancelAnimationFrame(frame);
  }, [open]);

  useEffect(() => {
    if (open) return;
    setEntered(false);
    const timer = window.setTimeout(() => onClosedRef.current?.(), reducedMotion() ? 0 : DURATION_MS + 40);
    return () => window.clearTimeout(timer);
  }, [open]);

  return (
    <div className={entered && open ? 'collapsible is-open' : 'collapsible'}>
      <div className="collapsible-inner">{children}</div>
    </div>
  );
}
