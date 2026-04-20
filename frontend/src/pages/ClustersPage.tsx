import { useCallback, useState } from "react";
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
import { SummaryCard } from "../components/SummaryCard";
import type { ClusterComment, ClusterSummary } from "../types/api";

export function ClustersPage() {
  const [docketId, setDocketId] = useState("");
  const [clusters, setClusters] = useState<ClusterSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);

  const [expanded, setExpanded] = useState<number | null>(null);
  const [comments, setComments] = useState<ClusterComment[]>([]);
  const [commentsLoading, setCommentsLoading] = useState(false);

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
    <div className="p-6 space-y-6">
      <h1 className="text-3xl font-bold">Comment Clusters</h1>

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
          className="rounded-lg bg-blue-600 px-6 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? "Loading..." : "Search"}
        </button>
      </form>

      {error && <div className="text-red-700">Error: {error}</div>}

      {searched && !loading && !error && clusters.length === 0 && (
        <div className="text-slate-500">
          No clusters found for this docket.
        </div>
      )}

      {clusters.length > 0 && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <SummaryCard label="Clusters" value={clusters.length} />
            <SummaryCard label="Total comments" value={totalComments} />
            <SummaryCard label="Labeled" value={`${labeledCount} / ${clusters.length}`} />
          </div>

          <section>
            <h2 className="text-xl font-semibold mb-3">Comments per cluster</h2>
            <div className="rounded-lg border border-slate-200 bg-white p-4 mb-6">
              <ResponsiveContainer width="100%" height={Math.max(200, clusters.length * 36)}>
                <BarChart
                  data={clusters.slice(0, 25).map((c) => ({
                    name: c.label ?? `#${c.cluster_id}`,
                    comments: c.comment_count,
                    clusterId: c.cluster_id,
                  }))}
                  layout="vertical"
                  margin={{ top: 4, right: 24, left: 8, bottom: 4 }}
                >
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                  <XAxis type="number" tick={{ fontSize: 12 }} />
                  <YAxis
                    type="category"
                    dataKey="name"
                    width={160}
                    tick={{ fontSize: 11 }}
                  />
                  <Tooltip />
                  <Bar dataKey="comments" radius={[0, 4, 4, 0]}>
                    {clusters.slice(0, 25).map((c) => (
                      <Cell
                        key={c.cluster_id}
                        fill={c.cluster_id === -1 ? "#94a3b8" : "#3b82f6"}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </section>

          <section>
            <h2 className="text-xl font-semibold mb-3">Clusters</h2>
            <ul className="space-y-3">
              {clusters.map((c) => (
                <li
                  key={c.cluster_id}
                  className="rounded-lg border border-slate-200 bg-white"
                >
                  <button
                    type="button"
                    className="w-full text-left p-4 hover:bg-slate-50 transition"
                    onClick={() => void toggleCluster(c.cluster_id)}
                  >
                    <div className="flex justify-between items-start">
                      <div>
                        <span className="font-medium text-slate-900">
                          {c.label ?? `Cluster #${c.cluster_id}`}
                        </span>
                        <span className="ml-2 text-sm text-slate-500">
                          ({c.comment_count} comments)
                        </span>
                      </div>
                      <span className="text-slate-400 text-sm">
                        {expanded === c.cluster_id ? "collapse" : "expand"}
                      </span>
                    </div>
                    {c.summary && (
                      <p className="mt-1 text-sm text-slate-600">{c.summary}</p>
                    )}
                  </button>

                  {expanded === c.cluster_id && (
                    <div className="border-t border-slate-100 p-4">
                      {commentsLoading ? (
                        <div className="text-sm text-slate-500">
                          Loading comments...
                        </div>
                      ) : comments.length === 0 ? (
                        <div className="text-sm text-slate-500">
                          No comments found.
                        </div>
                      ) : (
                        <ul className="space-y-2">
                          {comments.map((cm) => (
                            <li
                              key={cm.comment_id}
                              className="rounded border border-slate-100 p-3 text-sm"
                            >
                              <div className="text-xs text-slate-500 mb-1">
                                {cm.submitter_name ?? "Anonymous"} &middot;{" "}
                                {cm.comment_id}
                              </div>
                              <p className="text-slate-800 line-clamp-3">
                                {cm.comment_text ?? "(no text)"}
                              </p>
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  )}
                </li>
              ))}
            </ul>
          </section>
        </>
      )}
    </div>
  );
}
