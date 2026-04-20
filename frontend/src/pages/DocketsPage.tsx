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
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Dockets</h1>
        {!loading && total > 0 && (
          <span className="text-sm text-slate-500">
            {total.toLocaleString()} dockets
          </span>
        )}
      </div>

      <form className="flex gap-3" onSubmit={submit}>
        <input
          type="text"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search by docket ID…"
          className="flex-1 rounded-lg border border-slate-300 px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button
          type="submit"
          className="rounded-lg bg-blue-600 px-6 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          Search
        </button>
      </form>

      {error && <div className="text-red-700 text-sm">Error: {error}</div>}

      {loading && <div className="text-slate-500 text-sm">Loading…</div>}

      {!loading && !error && dockets.length === 0 && (
        <div className="text-slate-500 text-sm">
          {submittedQ
            ? `No dockets matching "${submittedQ}".`
            : "No dockets found. Run the pipeline to ingest data."}
        </div>
      )}

      {dockets.length > 0 && (
        <>
          <ul className="space-y-2">
            {dockets.map((d) => (
              <li
                key={d.docket_id}
                className="flex flex-col sm:flex-row sm:items-center justify-between rounded-lg border border-slate-200 bg-white px-4 py-3 gap-2"
              >
                <div>
                  <span className="font-medium text-slate-800">{d.docket_id}</span>
                  <span className="ml-3 text-sm text-slate-500">
                    {d.comment_count.toLocaleString()} comments
                  </span>
                </div>
                <div className="flex gap-2 text-xs">
                  <Link
                    to={`/clusters?docket=${encodeURIComponent(d.docket_id)}`}
                    className="rounded bg-slate-100 px-2 py-1 hover:bg-slate-200 text-slate-700"
                  >
                    Clusters
                  </Link>
                  <Link
                    to={`/graph?docket=${encodeURIComponent(d.docket_id)}`}
                    className="rounded bg-slate-100 px-2 py-1 hover:bg-slate-200 text-slate-700"
                  >
                    Graph
                  </Link>
                  <Link
                    to={`/query?docket=${encodeURIComponent(d.docket_id)}`}
                    className="rounded bg-slate-100 px-2 py-1 hover:bg-slate-200 text-slate-700"
                  >
                    Ask
                  </Link>
                </div>
              </li>
            ))}
          </ul>

          {pageCount > 1 && (
            <div className="flex items-center justify-between pt-2">
              <button
                type="button"
                disabled={page === 0}
                onClick={() => setPage((p) => p - 1)}
                className="rounded-lg border border-slate-200 px-4 py-2 text-sm hover:bg-slate-50 disabled:opacity-40"
              >
                ← Previous
              </button>
              <span className="text-sm text-slate-500">
                Page {page + 1} of {pageCount}
              </span>
              <button
                type="button"
                disabled={page >= pageCount - 1}
                onClick={() => setPage((p) => p + 1)}
                className="rounded-lg border border-slate-200 px-4 py-2 text-sm hover:bg-slate-50 disabled:opacity-40"
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
