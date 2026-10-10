import { useEffect, useState } from 'react';

const seatFromHash = () => new URLSearchParams(window.location.hash.slice(1)).get('seat');

/** The seat in the address (`#seat=ID`), kept in step with the browser's back and forward buttons. */
export function useSelectedSeat() {
  const [seatId, setSeatId] = useState<string | null>(seatFromHash);
  useEffect(() => {
    const onHashChange = () => setSeatId(seatFromHash());
    window.addEventListener('hashchange', onHashChange);
    return () => window.removeEventListener('hashchange', onHashChange);
  }, []);
  const choose = (id: string) => {
    window.location.hash = `seat=${id}`;
    setSeatId(id);
  };
  const clear = () => {
    window.history.replaceState(null, '', window.location.pathname + window.location.search);
    setSeatId(null);
  };
  return { seatId, choose, clear };
}
