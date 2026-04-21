import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getDockets } from "../api/client";
import type { DocketSummary } from "../types/api";

const PAGE_SIZE = 20;

export function DocketsPage() {
  const [q, setQ] = useState("");
  const [submittedQ, setSubmittedQ] = useState("");
  const [dockets, setDockets] = useState<DocketSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (query: string, pg: number) => {
    setLoading(true);
    setError(null);
    try {
      const res = await getDockets(query || undefined, PAGE_SIZE, pg * PAGE_SIZE);
      setDockets(res.items);
      setTotal(res.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
      setDockets([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load(submittedQ, page);
  }, [load, submittedQ, page]);

  const submit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      setPage(0);
      setSubmittedQ(q.trim());
    },
    [q],
  );

  const pageCount = Math.ceil(total / PAGE_SIZE);

  return (
    <div className="space-y-6">
      {/* header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-stone-800">Dockets</h1>
          <p className="mt-0.5 text-sm text-stone-500">
            Federal Register regulatory dockets
          </p>
        </div>
        {!loading && total > 0 && (
          <span className="rounded-full border border-stone-200 bg-white px-3 py-1 text-xs font-medium text-stone-600 shadow-sm">
            {total.toLocaleString()} total
          </span>
        )}
      </div>

      {/* search */}
      <form className="flex gap-3" onSubmit={submit}>
        <input
          type="text"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search by docket ID…"
          className="flex-1 rounded-lg border border-stone-300 bg-white px-4 py-2 text-sm text-stone-900 placeholder-stone-400 shadow-sm transition focus:border-amber-500 focus:outline-none focus:ring-1 focus:ring-amber-500"
        />
        <button
          type="submit"
          className="rounded-lg bg-gradient-to-r from-amber-500 to-rose-500 px-5 py-2 text-sm font-semibold text-white shadow-sm transition hover:shadow-md"
        >
          Search
        </button>
      </form>

      {/* states */}
      {error && (
        <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {error}
        </div>
      )}
      {loading && <div className="text-sm text-stone-500">Loading…</div>}

      {!loading && !error && dockets.length === 0 && (
        <div className="rounded-xl border border-stone-200 bg-white p-8 text-center shadow-sm">
          <p className="text-sm text-stone-600">
            {submittedQ
              ? `No dockets matching "${submittedQ}".`
              : "No dockets found. Run the pipeline to ingest data."}
          </p>
        </div>
      )}

      {/* list */}
      {dockets.length > 0 && (
        <>
          <div className="overflow-hidden rounded-2xl border border-stone-200 bg-white shadow-sm">
            {dockets.map((d, i) => (
              <div
                key={d.docket_id}
                className={`flex flex-col gap-3 px-5 py-4 transition hover:bg-stone-50 sm:flex-row sm:items-center sm:justify-between ${
                  i !== dockets.length - 1 ? "border-b border-stone-200/70" : ""
                }`}
              >
                <div>
                  <span className="font-mono text-sm font-medium text-stone-800">
                    {d.docket_id}
                  </span>
                  <span className="ml-3 text-xs text-stone-500">
                    {d.comment_count.toLocaleString()} comments
                  </span>
                </div>
                <div className="flex gap-2 text-xs">
                  <Link
                    to={`/clusters?docket=${encodeURIComponent(d.docket_id)}`}
                    className="rounded-full border border-stone-200 bg-white px-2.5 py-1 text-stone-700 transition hover:border-stone-300 hover:bg-stone-100"
                  >
                    Clusters
                  </Link>
                  <Link
                    to={`/graph?docket=${encodeURIComponent(d.docket_id)}`}
                    className="rounded-full border border-stone-200 bg-white px-2.5 py-1 text-stone-700 transition hover:border-stone-300 hover:bg-stone-100"
                  >
                    Graph
                  </Link>
                  <Link
                    to={`/query?docket=${encodeURIComponent(d.docket_id)}`}
                    className="rounded-full border border-stone-200 bg-white px-2.5 py-1 text-stone-700 transition hover:border-stone-300 hover:bg-stone-100"
                  >
                    Ask
                  </Link>
                </div>
              </div>
            ))}
          </div>

          {/* pagination */}
          {pageCount > 1 && (
            <div className="flex items-center justify-between pt-2">
              <button
                type="button"
                disabled={page === 0}
                onClick={() => setPage((p) => p - 1)}
                className="rounded-lg border border-stone-300 bg-white px-4 py-2 text-sm text-stone-700 shadow-sm transition hover:bg-stone-100 disabled:cursor-not-allowed disabled:opacity-40"
              >
                ← Previous
              </button>
              <span className="text-xs text-stone-500">
                Page {page + 1} of {pageCount}
              </span>
              <button
                type="button"
                disabled={page >= pageCount - 1}
                onClick={() => setPage((p) => p + 1)}
                className="rounded-lg border border-stone-300 bg-white px-4 py-2 text-sm text-stone-700 shadow-sm transition hover:bg-stone-100 disabled:cursor-not-allowed disabled:opacity-40"
              >
                Next →
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
