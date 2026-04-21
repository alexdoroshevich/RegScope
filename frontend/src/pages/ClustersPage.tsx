import { useCallback, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { getClusterComments, getClustersByDocket } from "../api/client";
import { DocketSearch } from "../components/DocketSearch";
import { PIIRevealBanner, PIIToggle } from "../components/PIIToggle";
import { SummaryCard } from "../components/SummaryCard";
import { formatSubmitter } from "../lib/pii";
import type { ClusterComment, ClusterSummary } from "../types/api";

export function ClustersPage() {
  const [searchParams] = useSearchParams();
  const [docketId, setDocketId] = useState(() => searchParams.get("docket") ?? "");
  const [clusters, setClusters] = useState<ClusterSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);

  const [expanded, setExpanded] = useState<number | null>(null);
  const [comments, setComments] = useState<ClusterComment[]>([]);
  const [commentsLoading, setCommentsLoading] = useState(false);

  const [revealPII, setRevealPII] = useState(false);

  const search = useCallback(async () => {
    const trimmed = docketId.trim();
    if (!trimmed) return;
    setLoading(true);
    setError(null);
    setSearched(true);
    setExpanded(null);
    setComments([]);
    try {
      const data = await getClustersByDocket(trimmed);
      setClusters(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
      setClusters([]);
    } finally {
      setLoading(false);
    }
  }, [docketId]);

  const toggleCluster = useCallback(
    async (clusterId: number) => {
      if (expanded === clusterId) {
        setExpanded(null);
        setComments([]);
        return;
      }
      setExpanded(clusterId);
      setCommentsLoading(true);
      try {
        const data = await getClusterComments(docketId.trim(), clusterId);
        setComments(data);
      } catch {
        setComments([]);
      } finally {
        setCommentsLoading(false);
      }
    },
    [docketId, expanded],
  );

  const totalComments = clusters.reduce((s, c) => s + c.comment_count, 0);
  const labeledCount = clusters.filter((c) => c.label !== null).length;

  return (
    <div className="space-y-8">
      {/* header */}
      <div>
        <div className="flex items-center gap-2">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-sky-100 text-sky-600 ring-1 ring-sky-200">
            ◎
          </span>
          <h1 className="text-2xl font-bold text-stone-800">Comment Clusters</h1>
        </div>
        <p className="mt-1 text-sm text-stone-500">
          Semantic topics discovered via HDBSCAN on sentence embeddings.
        </p>
      </div>

      {/* search */}
      <form
        className="flex gap-3"
        onSubmit={(e) => {
          e.preventDefault();
          void search();
        }}
      >
        <DocketSearch
          value={docketId}
          onChange={setDocketId}
          placeholder="Enter docket ID (e.g. EPA-HQ-OAR-2021-0317)"
          className="flex-1"
        />
        <button
          type="submit"
          disabled={loading || !docketId.trim()}
          className="rounded-lg bg-gradient-to-r from-amber-500 to-rose-500 px-5 py-2 text-sm font-semibold text-white shadow-sm transition hover:shadow-md disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loading ? "Loading…" : "Search"}
        </button>
      </form>

      {/* states */}
      {error && (
        <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {error}
        </div>
      )}

      {searched && !loading && !error && clusters.length === 0 && (
        <div className="rounded-xl border border-stone-200 bg-white p-8 text-center text-sm text-stone-500 shadow-sm">
          No clusters found for this docket.
        </div>
      )}

      {clusters.length > 0 && (
        <>
          {/* summary */}
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <SummaryCard label="Clusters" value={clusters.length} />
            <SummaryCard label="Total comments" value={totalComments} />
            <SummaryCard label="Labeled" value={`${labeledCount} / ${clusters.length}`} />
          </div>

          {/* chart */}
          <section className="space-y-3">
            <h2 className="text-xs font-semibold uppercase tracking-widest text-amber-600">
              Comments per cluster
            </h2>
            <div className="rounded-2xl border border-stone-200 bg-white p-5 shadow-sm">
              <ResponsiveContainer
                width="100%"
                height={Math.max(200, Math.min(clusters.length, 25) * 32 + 40)}
              >
                <BarChart
                  data={clusters.slice(0, 25).map((c) => ({
                    name: c.label ?? `#${c.cluster_id}`,
                    comments: c.comment_count,
                    clusterId: c.cluster_id,
                  }))}
                  layout="vertical"
                  margin={{ top: 4, right: 24, left: 8, bottom: 4 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#e7e5e4" horizontal={false} />
                  <XAxis
                    type="number"
                    tick={{ fontSize: 11, fill: "#78716c" }}
                    stroke="#d6d3d1"
                  />
                  <YAxis
                    type="category"
                    dataKey="name"
                    width={180}
                    tick={{ fontSize: 11, fill: "#44403c" }}
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
                    cursor={{ fill: "rgba(14,165,233,0.08)" }}
                  />
                  <Bar dataKey="comments" radius={[0, 4, 4, 0]}>
                    {clusters.slice(0, 25).map((c) => (
                      <Cell
                        key={c.cluster_id}
                        fill={c.cluster_id === -1 ? "#a8a29e" : "#38bdf8"}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </section>

          {/* cluster list */}
          <section className="space-y-3">
            <h2 className="text-xs font-semibold uppercase tracking-widest text-amber-600">
              Clusters
            </h2>
            <ul className="space-y-3">
              {clusters.map((c) => {
                const isOpen = expanded === c.cluster_id;
                const isNoise = c.cluster_id === -1;
                return (
                  <li
                    key={c.cluster_id}
                    className="overflow-hidden rounded-2xl border border-stone-200 bg-white shadow-sm transition hover:border-stone-300"
                  >
                    <button
                      type="button"
                      className="w-full px-5 py-4 text-left transition hover:bg-stone-50"
                      onClick={() => void toggleCluster(c.cluster_id)}
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex min-w-0 items-center gap-2">
                          <span
                            className={`h-2 w-2 shrink-0 rounded-full ${
                              isNoise ? "bg-stone-400" : "bg-sky-500"
                            }`}
                          />
                          <span className="truncate font-medium text-stone-800">
                            {c.label ?? `Cluster #${c.cluster_id}`}
                          </span>
                          {isNoise && (
                            <span className="rounded-full border border-stone-200 bg-stone-50 px-2 py-0.5 text-xs text-stone-500">
                              noise
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-3 text-xs text-stone-500">
                          <span className="tabular-nums">
                            {c.comment_count} comments
                          </span>
                          <span
                            className={`transition ${isOpen ? "rotate-180" : ""} text-stone-400`}
                            aria-hidden
                          >
                            ▾
                          </span>
                        </div>
                      </div>
                      {c.summary && (
                        <p className="mt-2 line-clamp-2 text-sm text-stone-600">
                          {c.summary}
                        </p>
                      )}
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
          </section>
        </>
      )}
    </div>
  );
}
