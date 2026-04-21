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
import { getAstroturfSummary, getDuplicateGroups, getGroupComments } from "../api/client";
import { PIIRevealBanner, PIIToggle } from "../components/PIIToggle";
import { SummaryCard } from "../components/SummaryCard";
import { formatSubmitter } from "../lib/pii";
import type { AstroturfSummary, ClusterComment, DuplicateGroup } from "../types/api";

const PAGE_SIZE = 20;

export function AstroturfPage() {
  const [summary, setSummary] = useState<AstroturfSummary | null>(null);
  const [groups, setGroups] = useState<DuplicateGroup[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Drill-down state
  const [expanded, setExpanded] = useState<number | null>(null);
  const [comments, setComments] = useState<ClusterComment[]>([]);
  const [commentsLoading, setCommentsLoading] = useState(false);

  // PII reveal — defaults to false (anonymised).
  const [revealPII, setRevealPII] = useState(false);

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

  const toggleGroup = useCallback(
    async (groupId: number) => {
      if (expanded === groupId) {
        setExpanded(null);
        setComments([]);
        return;
      }
      setExpanded(groupId);
      setCommentsLoading(true);
      try {
        const data = await getGroupComments(groupId);
        setComments(data);
      } catch {
        setComments([]);
      } finally {
        setCommentsLoading(false);
      }
    },
    [expanded],
  );

  if (loading && page === 0) {
    return <div className="text-sm text-stone-500">Loading…</div>;
  }
  if (error) {
    return (
      <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
        {error}
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* header */}
      <div>
        <div className="flex items-center gap-2">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-orange-100 text-orange-600 ring-1 ring-orange-200">
            ⚡
          </span>
          <h1 className="text-2xl font-bold text-stone-800">Astroturf Detection</h1>
        </div>
        <p className="mt-1 text-sm text-stone-500">
          MinHash-deduplicated comment groups, scored by campaign likelihood.
        </p>
      </div>

      {/* summary cards */}
      {summary && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
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
            label="Max likelihood"
            value={summary.max_campaign_likelihood.toFixed(2)}
          />
        </div>
      )}

      {/* chart */}
      {groups.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-xs font-semibold uppercase tracking-widest text-amber-600">
            Campaign likelihood (page {page + 1})
          </h2>
          <div className="rounded-2xl border border-stone-200 bg-white p-5 shadow-sm">
            <ResponsiveContainer width="100%" height={260}>
              <BarChart
                data={groups.map((g) => ({
                  name: `#${g.group_id}`,
                  likelihood: Number(g.campaign_likelihood.toFixed(2)),
                  size: g.group_size,
                }))}
                margin={{ top: 8, right: 16, left: 0, bottom: 8 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#e7e5e4" vertical={false} />
                <XAxis
                  dataKey="name"
                  tick={{ fontSize: 11, fill: "#78716c" }}
                  stroke="#d6d3d1"
                />
                <YAxis
                  tick={{ fontSize: 11, fill: "#78716c" }}
                  stroke="#d6d3d1"
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#ffffff",
                    border: "1px solid #e7e5e4",
                    borderRadius: 8,
                    fontSize: 12,
                    color: "#1c1917",
                    boxShadow: "0 4px 12px rgba(0,0,0,0.08)",
                  }}
                  cursor={{ fill: "rgba(251,146,60,0.10)" }}
                />
                <Bar dataKey="likelihood" fill="#fb923c" radius={[4, 4, 0, 0]} />
                <Bar dataKey="size" fill="#fed7aa" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>
      )}

      {/* groups list */}
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-xs font-semibold uppercase tracking-widest text-amber-600">
            Suspected campaigns{total > 0 ? ` · ${total}` : ""}
          </h2>
          {totalPages > 1 && (
            <span className="text-xs text-stone-500">
              Page {page + 1} of {totalPages}
            </span>
          )}
        </div>

        {groups.length === 0 ? (
          <div className="rounded-xl border border-stone-200 bg-white p-8 text-center text-sm text-stone-500 shadow-sm">
            No astroturf groups detected. Run the dedup pipeline to populate.
          </div>
        ) : (
          <ul className="space-y-3">
            {groups.map((g) => {
              const isOpen = expanded === g.group_id;
              return (
                <li
                  key={g.group_id}
                  className="overflow-hidden rounded-2xl border border-stone-200 bg-white shadow-sm transition hover:border-stone-300"
                >
                  <button
                    type="button"
                    className="w-full px-5 py-4 text-left transition hover:bg-stone-50"
                    onClick={() => void toggleGroup(g.group_id)}
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-sm font-medium text-stone-700">
                          #{g.group_id}
                        </span>
                        <span className="rounded-full border border-rose-200 bg-rose-50 px-2 py-0.5 text-xs font-medium text-rose-700">
                          {g.campaign_likelihood.toFixed(2)}×
                        </span>
                      </div>
                      <div className="flex items-center gap-3 text-xs text-stone-500">
                        <span className="tabular-nums">
                          {g.group_size} comments · {g.unique_submitters} submitters
                        </span>
                        <span
                          className={`transition ${isOpen ? "rotate-180" : ""} text-stone-400`}
                          aria-hidden
                        >
                          ▾
                        </span>
                      </div>
                    </div>
                    <p className="mt-3 line-clamp-2 text-sm text-stone-600">
                      {g.template_text ?? "(no template)"}
                    </p>
                  </button>

                  {isOpen && (
                    <div className="border-t border-stone-200/70 bg-stone-50/70 px-5 py-4">
                      {commentsLoading ? (
                        <div className="text-sm text-stone-500">Loading comments…</div>
                      ) : comments.length === 0 ? (
                        <div className="text-sm text-stone-500">No comments found.</div>
                      ) : (
                        <>
                          <PIIToggle
                            revealed={revealPII}
                            onToggle={() => setRevealPII((v) => !v)}
                            count={comments.length}
                          />
                          {revealPII && <PIIRevealBanner />}
                          <ul className="space-y-2">
                            {comments.map((cm) => (
                              <li
                                key={cm.comment_id}
                                className="rounded-lg border border-stone-200 bg-white p-3 text-sm shadow-sm"
                              >
                                <div className="mb-1 flex items-center gap-2 text-xs text-stone-500">
                                  <span className="font-medium text-stone-600">
                                    {formatSubmitter(cm.submitter_name, cm.comment_id, revealPII)}
                                  </span>
                                  <span className="text-stone-400">·</span>
                                  <span className="font-mono text-stone-400">
                                    {cm.comment_id}
                                  </span>
                                </div>
                                <p className="line-clamp-3 text-stone-700">
                                  {cm.comment_text ?? "(no text)"}
                                </p>
                              </li>
                            ))}
                          </ul>
                        </>
                      )}
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
        )}

        {totalPages > 1 && (
          <div className="flex items-center justify-between pt-2">
            <button
              type="button"
              onClick={() => setPage((p) => p - 1)}
              disabled={page === 0 || loading}
              className="rounded-lg border border-stone-300 bg-white px-4 py-2 text-sm text-stone-700 shadow-sm transition hover:bg-stone-100 disabled:cursor-not-allowed disabled:opacity-40"
            >
              ← Previous
            </button>
            <span className="text-xs text-stone-500 tabular-nums">
              {page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, total)} of {total}
            </span>
            <button
              type="button"
              onClick={() => setPage((p) => p + 1)}
              disabled={page >= totalPages - 1 || loading}
              className="rounded-lg border border-stone-300 bg-white px-4 py-2 text-sm text-stone-700 shadow-sm transition hover:bg-stone-100 disabled:cursor-not-allowed disabled:opacity-40"
            >
              Next →
            </button>
          </div>
        )}
      </section>
    </div>
  );
}
