import { useMemo, useState } from 'react';
import { nameContains, nameEquals } from './filters';
import type { SeatRow } from './rows';

const MAX_SUGGESTIONS = 8;

/** A search box with its own list of matching seat names. */
export function SeatSearch({
  rows,
  query,
  onQueryChange,
  onChoose,
  onPick,
}: {
  rows: SeatRow[];
  query: string;
  onQueryChange: (query: string) => void;
  /** Called when the typed text is exactly a seat name. */
  onChoose: (id: string) => void;
  /** Called when a suggestion is clicked or Enter is pressed. */
  onPick: (id: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const suggestions = useMemo(
    () =>
      query.trim()
        ? rows
            .filter((row) => nameContains(row, query))
            .sort((a, b) => a.name.localeCompare(b.name, 'en-NZ'))
            .slice(0, MAX_SUGGESTIONS)
        : [],
    [rows, query],
  );
  const pickSuggestion = (row: SeatRow) => {
    onQueryChange(row.name);
    setOpen(false);
    onPick(row.id);
  };
  return (
    <div
      className="find"
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setOpen(false);
      }}
    >
      <label>
        Find a seat
        <input
          type="search"
          value={query}
          placeholder="Type a seat name"
          autoComplete="off"
          role="combobox"
          aria-expanded={open && suggestions.length > 0}
          aria-controls="seat-suggestions"
          onFocus={() => setOpen(true)}
          onKeyDown={(event) => {
            if (event.key === 'Escape') setOpen(false);
            if (event.key === 'Enter' && suggestions[0]) pickSuggestion(suggestions[0]);
          }}
          onChange={(event) => {
            onQueryChange(event.target.value);
            setOpen(true);
            const exact = rows.find((row) => nameEquals(row, event.target.value));
            if (exact) onChoose(exact.id);
          }}
        />
      </label>
      {open && suggestions.length > 0 && (
        <ul className="suggest" id="seat-suggestions" role="listbox">
          {suggestions.map((row) => (
            <li key={row.id} role="option" aria-selected={false}>
              <button
                type="button"
                tabIndex={-1}
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => pickSuggestion(row)}
              >
                {row.name}
                {row.kind === 'maori' ? ' (Māori)' : ''}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
