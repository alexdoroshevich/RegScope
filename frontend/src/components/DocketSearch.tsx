import { useCallback, useEffect, useRef, useState } from "react";
import { getDockets } from "../api/client";
import type { DocketSummary } from "../types/api";

interface Props {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  /** Extra Tailwind classes forwarded to the wrapper div (e.g. "flex-1", "w-full"). */
  className?: string;
}

/**
 * Controlled text input with docket-ID autocomplete.
 *
 * Fires a debounced GET /api/v1/dockets?q=<value> once the user has
 * typed at least 2 characters and displays a listbox of matching dockets.
 * Selecting a suggestion writes the docket ID back via `onChange`.
 */
export function DocketSearch({ value, onChange, placeholder, className }: Props) {
  const [suggestions, setSuggestions] = useState<DocketSummary[]>([]);
  const [open, setOpen] = useState(false);
  const [fetching, setFetching] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Debounced fetch whenever the value changes.
  useEffect(() => {
    const q = value.trim();
    if (q.length < 2) {
      setSuggestions([]);
      setOpen(false);
      return;
    }

    if (debounceRef.current !== null) {
      clearTimeout(debounceRef.current);
    }

    let cancelled = false;

    debounceRef.current = setTimeout(() => {
      setFetching(true);
      getDockets(q, 8)
        .then((res) => {
          if (!cancelled) {
            setSuggestions(res.items);
            setOpen(res.items.length > 0);
          }
        })
        .catch(() => {
          if (!cancelled) {
            setSuggestions([]);
            setOpen(false);
          }
        })
        .finally(() => {
          if (!cancelled) setFetching(false);
        });
    }, 300);

    return () => {
      cancelled = true;
      if (debounceRef.current !== null) {
        clearTimeout(debounceRef.current);
      }
    };
  }, [value]);

  // Close the dropdown on click outside.
  useEffect(() => {
    function handleOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleOutside);
    return () => document.removeEventListener("mousedown", handleOutside);
  }, []);

  const select = useCallback(
    (docketId: string) => {
      onChange(docketId);
      setOpen(false);
      setSuggestions([]);
    },
    [onChange],
  );

  return (
    <div ref={containerRef} className={`relative ${className ?? ""}`}>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        aria-autocomplete="list"
        aria-haspopup="listbox"
        aria-expanded={open}
        className="w-full rounded-lg border border-slate-300 px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
      />
      {fetching && (
        <span className="absolute right-3 top-2.5 text-xs text-slate-400" aria-hidden="true">
          …
        </span>
      )}
      {open && (
        <ul
          role="listbox"
          className="absolute z-10 mt-1 w-full rounded-lg border border-slate-200 bg-white shadow-lg max-h-60 overflow-y-auto"
        >
          {suggestions.map((d) => (
            <li
              key={d.docket_id}
              role="option"
              aria-selected={value === d.docket_id}
              className="flex items-center justify-between px-4 py-2 text-sm hover:bg-slate-50 cursor-pointer"
              // onMouseDown+preventDefault keeps focus on the input so
              // the blur event does not close the dropdown before onClick fires.
              onMouseDown={(e) => {
                e.preventDefault();
                select(d.docket_id);
              }}
            >
              <span className="font-medium text-slate-800">{d.docket_id}</span>
              <span className="text-xs text-slate-400">
                {d.comment_count.toLocaleString()} comments
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
