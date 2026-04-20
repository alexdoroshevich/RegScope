import { useCallback, useState } from "react";
import { ForceGraph2D } from "react-force-graph";
import { getCitationGraph } from "../api/client";
import { DocketSearch } from "../components/DocketSearch";
import type { GraphResponse } from "../types/api";

// Node/link shapes expected by ForceGraph2D at runtime (id, source, target are required).
interface FGNode {
  id: string;
  label: string;
  type: string;
  count: number;
}

interface FGLink {
  source: string;
  target: string;
  value: number;
}

const NODE_COLOR: Record<string, string> = {
  docket: "#3b82f6",      // blue-500
  regulation: "#10b981",  // emerald-500
};

export function GraphPage() {
  const [docketId, setDocketId] = useState("");
  const [graph, setGraph] = useState<GraphResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);

  const search = useCallback(async () => {
    const trimmed = docketId.trim();
    if (!trimmed) return;
    setLoading(true);
    setError(null);
    setSearched(true);
    try {
      const data = await getCitationGraph(trimmed);
      setGraph(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
      setGraph(null);
    } finally {
      setLoading(false);
    }
  }, [docketId]);

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-3xl font-bold">Citation Graph</h1>
      <p className="text-slate-600 text-sm">
        Visualizes which CFR and U.S.C. regulations a docket&apos;s comments
        reference most. Node size reflects citation frequency.
      </p>

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
          placeholder="Enter docket ID (e.g. DEMO-2024-0001)"
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

      {error && <div className="text-red-700 text-sm">Error: {error}</div>}

      {searched && !loading && !error && graph?.nodes.length === 0 && (
        <div className="text-slate-500 text-sm">
          No citations found for this docket. Run the pipeline to extract them.
        </div>
      )}

      {graph && graph.nodes.length > 0 && (
        <>
          <div className="flex gap-4 text-sm text-slate-600">
            <span>
              <span
                className="inline-block w-3 h-3 rounded-full mr-1"
                style={{ background: NODE_COLOR.docket }}
              />
              Docket
            </span>
            <span>
              <span
                className="inline-block w-3 h-3 rounded-full mr-1"
                style={{ background: NODE_COLOR.regulation }}
              />
              Regulation (
              {graph.nodes.filter((n) => n.type === "regulation").length} unique)
            </span>
          </div>

          <div className="rounded-lg border border-slate-200 bg-white overflow-hidden">
            <ForceGraph2D
              graphData={{
                nodes: graph.nodes as FGNode[],
                links: graph.links as FGLink[],
              }}
              nodeId="id"
              nodeLabel={(n: FGNode) => `${n.label} (${n.count} comments)`}
              nodeColor={(n: FGNode) => NODE_COLOR[n.type] ?? "#94a3b8"}
              nodeVal={(n: FGNode) => Math.max(3, Math.sqrt(n.count + 1) * 4)}
              linkSource="source"
              linkTarget="target"
              linkWidth={(l: FGLink) => Math.max(1, Math.log2((l.value ?? 1) + 1))}
              linkLabel={(l: FGLink) => `${l.value} comments`}
              width={900}
              height={500}
              backgroundColor="#f8fafc"
            />
          </div>

          <section>
            <h2 className="text-xl font-semibold mb-3">Top cited regulations</h2>
            <ul className="space-y-2">
              {graph.nodes
                .filter((n) => n.type === "regulation")
                .sort((a, b) => b.count - a.count)
                .slice(0, 10)
                .map((n) => (
                  <li
                    key={n.id}
                    className="flex items-center justify-between rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm"
                  >
                    <span className="font-medium text-slate-800">{n.label}</span>
                    <span className="text-slate-500">{n.count} comments</span>
                  </li>
                ))}
            </ul>
          </section>
        </>
      )}
    </div>
  );
}
