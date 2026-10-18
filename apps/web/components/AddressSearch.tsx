"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useId, useMemo, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import { searchAddresses } from "@/lib/api";
import { SEARCH } from "@/lib/config";
import { formatCurrency, formatDate } from "@/lib/format";
import { highlightSegments } from "@/lib/highlight";
import type { AddressResult } from "@/lib/types";
import { TypeBadge } from "./TypeBadge";

export type SearchFn = (q: string, signal: AbortSignal) => Promise<AddressResult[]>;

const defaultSearch: SearchFn = (q, signal) => searchAddresses(q, { signal, limit: SEARCH.limit });

interface Settled {
  query: string;
  items: AddressResult[];
  error: boolean;
}

export interface AddressSearchProps {
  onSelect?: (result: AddressResult) => void;
  search?: SearchFn;
  size?: "md" | "lg";
  label?: string;
  placeholder?: string;
  autoFocus?: boolean;
}

export function Highlight({ text, query }: { text: string; query: string }): ReactNode {
  return highlightSegments(text, query).map((seg, i) =>
    seg.match ? (
      <mark key={i} className="rounded-sm bg-amber-200/80 px-0 font-semibold text-inherit dark:bg-amber-400/30">
        {seg.text}
      </mark>
    ) : (
      <span key={i}>{seg.text}</span>
    ),
  );
}

export function AddressSearch({
  onSelect,
  search = defaultSearch,
  size = "md",
  label = "Search by address",
  placeholder = "Enter a street address, e.g. 12 Example St",
  autoFocus,
}: AddressSearchProps) {
  const router = useRouter();
  const uid = useId();
  const listId = `${uid}-listbox`;
  const optId = (i: number) => `${uid}-opt-${i}`;

  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const [settled, setSettled] = useState<Settled | null>(null);
  const [selectedText, setSelectedText] = useState<string | null>(null);
  const [retryKey, setRetryKey] = useState(0);
  const listRef = useRef<HTMLUListElement>(null);

  const trimmed = query.trim();
  const eligible = trimmed.length >= SEARCH.minChars;
  const current = settled && settled.query === trimmed ? settled : null;
  const loading = eligible && !current;
  const items = useMemo(() => current?.items ?? [], [current]);
  const visible = open && eligible && trimmed !== selectedText;
  const listVisible = visible && items.length > 0;

  // Debounced fetch; cleanup aborts the in-flight request, so stale responses are dropped.
  useEffect(() => {
    if (!eligible || trimmed === selectedText) return;
    const ctrl = new AbortController();
    const timer = setTimeout(async () => {
      try {
        const results = await search(trimmed, ctrl.signal);
        if (!ctrl.signal.aborted) setSettled({ query: trimmed, items: results.slice(0, SEARCH.limit), error: false });
      } catch {
        if (!ctrl.signal.aborted) setSettled({ query: trimmed, items: [], error: true });
      }
    }, SEARCH.debounceMs);
    return () => {
      clearTimeout(timer);
      ctrl.abort();
    };
  }, [trimmed, eligible, search, selectedText, retryKey]);

  useEffect(() => {
    if (activeIndex < 0) return;
    document.getElementById(optId(activeIndex))?.scrollIntoView({ block: "nearest" });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeIndex]);

  const select = useCallback(
    (r: AddressResult) => {
      setSelectedText(r.display.trim());
      setQuery(r.display);
      setOpen(false);
      setActiveIndex(-1);
      if (onSelect) onSelect(r);
      else router.push(`/property/${encodeURIComponent(r.property_id)}`);
    },
    [onSelect, router],
  );

  function onKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    const n = items.length;
    switch (e.key) {
      case "ArrowDown":
        if (!eligible) return;
        e.preventDefault();
        if (!visible) setOpen(true);
        if (n) setActiveIndex((i) => (i + 1) % n);
        break;
      case "ArrowUp":
        if (!eligible) return;
        e.preventDefault();
        if (!visible) setOpen(true);
        if (n) setActiveIndex((i) => (i <= 0 ? n - 1 : i - 1));
        break;
      case "Home":
        if (listVisible) {
          e.preventDefault();
          setActiveIndex(0);
        }
        break;
      case "End":
        if (listVisible) {
          e.preventDefault();
          setActiveIndex(n - 1);
        }
        break;
      case "Enter":
        if (listVisible) {
          e.preventDefault();
          const target = items[activeIndex >= 0 ? activeIndex : 0];
          if (target) select(target);
        }
        break;
      case "Escape":
        if (visible) {
          e.preventDefault();
          setOpen(false);
          setActiveIndex(-1);
        } else if (query) {
          e.preventDefault();
          setQuery("");
        }
        break;
    }
  }

  const status = !visible
    ? ""
    : loading
      ? "Searching"
      : current?.error
        ? "Search failed"
        : items.length
          ? `${items.length} ${items.length === 1 ? "suggestion" : "suggestions"} available. Use up and down arrows to review.`
          : "No matching addresses";

  const big = size === "lg";

  return (
    <div
      className="relative w-full"
      onBlur={(e) => {
        if (!e.currentTarget.contains(e.relatedTarget)) {
          setOpen(false);
          setActiveIndex(-1);
        }
      }}
    >
      <label htmlFor={`${uid}-input`} className="sr-only">
        {label}
      </label>
      <div className="relative">
        <svg
          className={`pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-muted ${big ? "h-6 w-6" : "h-5 w-5"}`}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          aria-hidden="true"
        >
          <circle cx="11" cy="11" r="7" />
          <path d="M20 20l-3.5-3.5" />
        </svg>
        <input
          id={`${uid}-input`}
          type="text"
          role="combobox"
          aria-expanded={listVisible}
          aria-controls={listId}
          aria-autocomplete="list"
          aria-activedescendant={listVisible && activeIndex >= 0 ? optId(activeIndex) : undefined}
          autoComplete="off"
          autoCorrect="off"
          spellCheck={false}
          autoFocus={autoFocus}
          enterKeyHint="search"
          placeholder={placeholder}
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setSelectedText(null);
            setOpen(true);
            setActiveIndex(-1);
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={onKeyDown}
          className={`w-full rounded-xl border border-line bg-surface pl-12 pr-12 text-fg shadow-sm placeholder:text-muted/80 focus:border-brand focus:outline-none focus:ring-2 focus:ring-brand/40 ${
            big ? "h-14 text-lg" : "h-11 text-base"
          }`}
        />
        {loading && visible && (
          <span
            aria-hidden="true"
            className="absolute right-4 top-1/2 h-5 w-5 -translate-y-1/2 animate-spin rounded-full border-2 border-line border-t-brand"
          />
        )}
      </div>

      <div role="status" aria-live="polite" className="sr-only">
        {status}
      </div>

      {visible && (
        <div className="absolute left-0 right-0 top-full z-30 mt-2 overflow-hidden rounded-xl border border-line bg-surface text-left shadow-xl">
          {loading && <p className="px-4 py-3 text-sm text-muted">Searching…</p>}

          {current?.error && (
            <div role="alert" className="flex items-center justify-between gap-3 px-4 py-3 text-sm">
              <span className="text-rose-600 dark:text-rose-400">Couldn’t load suggestions.</span>
              <button
                type="button"
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => {
                  setSettled(null);
                  setRetryKey((k) => k + 1);
                }}
                className="font-semibold text-brand hover:underline"
              >
                Retry
              </button>
            </div>
          )}

          {current && !current.error && items.length === 0 && (
            <p className="px-4 py-3 text-sm text-muted">No matching addresses found.</p>
          )}

          {items.length > 0 && (
            <ul id={listId} ref={listRef} role="listbox" aria-label="Address suggestions" className="max-h-96 overflow-auto py-1">
              {items.map((r, i) => {
                const active = i === activeIndex;
                return (
                  <li
                    key={r.property_id}
                    id={optId(i)}
                    role="option"
                    aria-selected={active}
                    onMouseDown={(e) => e.preventDefault()}
                    onMouseMove={() => i !== activeIndex && setActiveIndex(i)}
                    onClick={() => select(r)}
                    className={`flex cursor-pointer flex-col gap-1 px-4 py-3 sm:flex-row sm:items-center sm:justify-between sm:gap-4 ${
                      active ? "bg-brand-soft" : ""
                    }`}
                  >
                    <div className="min-w-0">
                      <div className="truncate font-medium">
                        <Highlight text={r.address} query={trimmed} />
                      </div>
                      <div className="truncate text-sm text-muted">
                        <Highlight text={`${r.suburb} ${r.state} ${r.postcode}`} query={trimmed} />
                      </div>
                    </div>
                    <div className="flex shrink-0 items-center gap-3 text-sm">
                      <TypeBadge type={r.property_type} />
                      <span className="text-right">
                        <span className="block font-semibold">{formatCurrency(r.last_sale_price)}</span>
                        {r.last_sale_date && (
                          <span className="block text-xs text-muted">{formatDate(r.last_sale_date)}</span>
                        )}
                      </span>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
