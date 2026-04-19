import { useCallback, useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { getAstroturfSummary, getDuplicateGroups } from "../api/client";
import { SummaryCard } from "../components/SummaryCard";
import type { AstroturfSummary, DuplicateGroup } from "../types/api";

const PAGE_SIZE = 20;

export function AstroturfPage() {
  const [summary, setSummary] = useState<AstroturfSummary | null>(null);
  const [groups, setGroups] = useState<DuplicateGroup[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const loadPage = useCallback(
    async (p: number) => {
      setLoading(true);
      setError(null);
      try {
        const [s, g] = await Promise.all([
          page === 0 ? getAstroturfSummary() : Promise.resolve(summary!),
          getDuplicateGroups(true, PAGE_SIZE, p * PAGE_SIZE),
        ]);
        setSummary(s as AstroturfSummary);
        setGroups(g.items);
        setTotal(g.total);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
      } finally {
        setLoading(false);
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [page],
  );

  useEffect(() => {
    void loadPage(page);
  }, [loadPage, page]);

  if (loading && page === 0) return <div className="p-6">Loading…</div>;
  if (error) return <div className="p-6 text-red-700">Error: {error}</div>;

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-3xl font-bold">Astroturf Detection</h1>

      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <SummaryCard label="Total groups" value={summary.total_groups} />
          <SummaryCard
            label="Astroturf groups"
            value={summary.astroturf_groups}
            tone="warning"
          />
          <SummaryCard
            label="Flagged comments"
            value={summary.total_flagged_comments}
          />
          <SummaryCard
            label="Max campaign likelihood"
            value={summary.max_campaign_likelihood.toFixed(2)}
          />
        </div>
      )}

      {groups.length > 0 && (
        <section>
          <h2 className="text-xl font-semibold mb-3">Campaign likelihood</h2>
          <div className="rounded-lg border border-slate-200 bg-white p-4">
            <ResponsiveContainer width="100%" height={260}>
              <BarChart
                data={groups.map((g) => ({
                  name: `#${g.group_id}`,
                  likelihood: Number(g.campaign_likelihood.toFixed(2)),
                  size: g.group_size,
                }))}
                margin={{ top: 8, right: 16, left: 0, bottom: 8 }}
              >
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip />
                <Bar dataKey="likelihood" fill="#ef4444" radius={[4, 4, 0, 0]} />
                <Bar dataKey="size" fill="#fca5a5" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>
      )}

      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-xl font-semibold">
            Suspected campaigns{total > 0 ? ` (${total} total)` : ""}
          </h2>
          {totalPages > 1 && (
            <span className="text-sm text-slate-500">
              Page {page + 1} of {totalPages}
            </span>
          )}
        </div>

        <ul className="space-y-3">
          {groups.map((g) => (
            <li
              key={g.group_id}
              className="rounded-lg border border-slate-200 bg-white p-4"
            >
              <div className="flex justify-between text-sm text-slate-600">
                <span>Group #{g.group_id}</span>
                <span>
                  {g.group_size} comments / {g.unique_submitters} submitters
                </span>
              </div>
              <p className="mt-2 text-slate-800 line-clamp-2">
                {g.template_text ?? "(no template)"}
              </p>
              <div className="mt-2 text-xs text-red-700 font-medium">
                Likelihood: {g.campaign_likelihood.toFixed(2)}
              </div>
            </li>
          ))}
        </ul>

        {totalPages > 1 && (
          <div className="flex items-center justify-between mt-4">
            <button
              type="button"
              onClick={() => setPage((p) => p - 1)}
              disabled={page === 0 || loading}
              className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-40"
            >
              ← Previous
            </button>
            <span className="text-sm text-slate-500">
              {page * PAGE_SIZE + 1}–
              {Math.min((page + 1) * PAGE_SIZE, total)} of {total}
            </span>
            <button
              type="button"
              onClick={() => setPage((p) => p + 1)}
              disabled={page >= totalPages - 1 || loading}
              className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-40"
            >
              Next →
            </button>
          </div>
        )}
      </section>
    </div>
  );
}
