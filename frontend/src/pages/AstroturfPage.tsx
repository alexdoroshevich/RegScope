import { useEffect, useState } from "react";
import { getAstroturfSummary, getDuplicateGroups } from "../api/client";
import { SummaryCard } from "../components/SummaryCard";
import type { AstroturfSummary, DuplicateGroup } from "../types/api";

export function AstroturfPage() {
  const [summary, setSummary] = useState<AstroturfSummary | null>(null);
  const [groups, setGroups] = useState<DuplicateGroup[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [s, g] = await Promise.all([
          getAstroturfSummary(),
          getDuplicateGroups(true, 20, 0),
        ]);
        if (!cancelled) {
          setSummary(s);
          setGroups(g.items);
          setLoading(false);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Unknown error");
          setLoading(false);
        }
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) return <div className="p-6">Loading…</div>;
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
      <section>
        <h2 className="text-xl font-semibold mb-3">
          Suspected campaigns ({groups.length})
        </h2>
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
      </section>
    </div>
  );
}
