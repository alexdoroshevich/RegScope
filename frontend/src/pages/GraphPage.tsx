import { useCallback, useState } from "react";
import { useSearchParams } from "react-router-dom";
// react-force-graph-2d is a 2D-only package — does not pull in three.js or A-Frame,
// so it avoids the react-force-graph compatibility hacks (window.THREE shim, etc.).
import ForceGraph2D from "react-force-graph-2d";
import { getCitationGraph } from "../api/client";
import { DocketSearch } from "../components/DocketSearch";
import type { GraphResponse } from "../types/api";

// Node/link shapes expected by ForceGraph2D at runtime (id, source, target are required).
// x/y are populated by the force-simulation and are undefined on the first render tick.
interface FGNode {
  id: string;
  label: string;
  type: string;
  count: number;
  x?: number;
  y?: number;
}

interface FGLink {
  source: string;
  target: string;
  value: number;
}

const NODE_COLOR: Record<string, string> = {
  docket: "#f59e0b",      // amber-500
  regulation: "#10b981",  // emerald-500
};

export function GraphPage() {
  const [searchParams] = useSearchParams();
  const [docketId, setDocketId] = useState(() => searchParams.get("docket") ?? "");
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
    <div className="space-y-8">
      {/* header */}
      <div>
        <div className="flex items-center gap-2">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-100 text-emerald-600 ring-1 ring-emerald-200">
            ⬡
          </span>
          <h1 className="text-2xl font-bold text-stone-800">Citation Graph</h1>
        </div>
        <p className="mt-1 max-w-2xl text-sm text-stone-500">
          Which CFR and U.S.C. regulations does a docket&apos;s comments reference?
          Node size reflects citation frequency.
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
          placeholder="Enter docket ID (e.g. DEMO-2024-0001)"
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

      {searched && !loading && !error && graph?.nodes.length === 0 && (
        <div className="rounded-xl border border-stone-200 bg-white p-8 text-center text-sm text-stone-500 shadow-sm">
          No citations found for this docket. Run the pipeline to extract them.
        </div>
      )}

      {graph && graph.nodes.length > 0 && (
        <>
          {/* legend */}
          <div className="flex flex-wrap gap-2 text-xs text-stone-600">
            <span className="inline-flex items-center gap-2 rounded-full border border-stone-200 bg-white px-3 py-1 shadow-sm">
              <span
                className="h-2 w-2 rounded-full"
                style={{ background: NODE_COLOR.docket }}
              />
              Docket
            </span>
            <span className="inline-flex items-center gap-2 rounded-full border border-stone-200 bg-white px-3 py-1 shadow-sm">
              <span
                className="h-2 w-2 rounded-full"
                style={{ background: NODE_COLOR.regulation }}
              />
              Regulation
              <span className="text-stone-400">
                ({graph.nodes.filter((n) => n.type === "regulation").length} unique)
              </span>
            </span>
          </div>

          {/* graph canvas */}
          <div className="overflow-hidden rounded-2xl border border-stone-200 bg-white shadow-sm">
            <ForceGraph2D
              graphData={{
                nodes: graph.nodes as FGNode[],
                links: graph.links as FGLink[],
              }}
              nodeId="id"
              nodeLabel={(n: FGNode) => `${n.label} (${n.count} comments)`}
              nodeColor={(n: FGNode) => NODE_COLOR[n.type] ?? "#a8a29e"}
              nodeVal={(n: FGNode) => Math.max(8, Math.sqrt(n.count + 1) * 6)}
              // Draw the node's label under the default circle. Mode "after"
              // runs our callback AFTER the default node is rendered, so we
              // only add the text.
              nodeCanvasObjectMode={() => "after"}
              nodeCanvasObject={(node: FGNode, ctx, globalScale) => {
                const label = node.label;
                const fontSize = Math.max(10, 12 / globalScale);
                ctx.font = `${fontSize}px ui-sans-serif, system-ui, sans-serif`;
                ctx.textAlign = "center";
                ctx.textBaseline = "top";
                const radius = Math.max(8, Math.sqrt(node.count + 1) * 6);
                // Measure for a pill background so labels are legible over edges.
                const padX = 4;
                const padY = 2;
                const textWidth = ctx.measureText(label).width;
                const x = node.x ?? 0;
                const y = (node.y ?? 0) + radius + 3;
                ctx.fillStyle = "rgba(250, 250, 249, 0.92)";
                ctx.fillRect(
                  x - textWidth / 2 - padX,
                  y - padY,
                  textWidth + padX * 2,
                  fontSize + padY * 2,
                );
                ctx.fillStyle = "#44403c";
                ctx.fillText(label, x, y);
              }}
              linkSource="source"
              linkTarget="target"
              linkColor={() => "rgba(120,113,108,0.35)"}
              linkWidth={(l: FGLink) => Math.max(1.5, Math.log2((l.value ?? 1) + 1) * 1.2)}
              linkLabel={(l: FGLink) => `${l.value} comments`}
              cooldownTicks={60}
              width={900}
              height={500}
              backgroundColor="#fafaf9"
            />
          </div>

          {/* top cited list */}
          <section className="space-y-3">
            <h2 className="text-xs font-semibold uppercase tracking-widest text-amber-600">
              Top cited regulations
            </h2>
            <div className="overflow-hidden rounded-2xl border border-stone-200 bg-white shadow-sm">
              {graph.nodes
                .filter((n) => n.type === "regulation")
                .sort((a, b) => b.count - a.count)
                .slice(0, 10)
                .map((n, i, arr) => (
                  <div
                    key={n.id}
                    className={`flex items-center justify-between px-5 py-3 text-sm transition hover:bg-stone-50 ${
                      i !== arr.length - 1 ? "border-b border-stone-200/70" : ""
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <span className="font-mono text-xs text-stone-400 tabular-nums">
                        {(i + 1).toString().padStart(2, "0")}
                      </span>
                      <span className="font-medium text-stone-800">{n.label}</span>
                    </div>
                    <span className="text-xs text-stone-500 tabular-nums">
                      {n.count} comments
                    </span>
                  </div>
                ))}
            </div>
          </section>
        </>
      )}
    </div>
  );
}
