import { useCallback, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Layer,
  Rectangle,
  ResponsiveContainer,
  Sankey,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { getCitationGraph } from "../api/client";
import { DocketSearch } from "../components/DocketSearch";
import type { GraphResponse } from "../types/api";

// Colours match the per-feature accents elsewhere in the app.
const DOCKET_COLOR = "#f59e0b"; // amber-500
const REG_COLOR = "#10b981";    // emerald-500

// Two ways to read the same data. Sankey is the default — it spatially
// encodes citation flow in a way that's readable for any number of
// regulations. The bar view is strictly sorted by count.
type View = "sankey" | "bars";

interface SankeyDatum {
  nodes: { name: string; type: "docket" | "regulation" }[];
  links: { source: number; target: number; value: number }[];
}

interface NodePayload {
  name: string;
  type?: "docket" | "regulation";
  value?: number;
}

interface LinkPayload {
  source: { name: string };
  target: { name: string };
  value: number;
}

/** Draw a Sankey node as a coloured rectangle with an external label. */
function SankeyNode({
  x,
  y,
  width,
  height,
  payload,
  containerWidth,
}: {
  x: number;
  y: number;
  width: number;
  height: number;
  payload: NodePayload;
  containerWidth: number;
}) {
  const isOut = x + width + 6 > containerWidth;
  const fill = payload.type === "docket" ? DOCKET_COLOR : REG_COLOR;
  return (
    <Layer key={`node-${payload.name}`}>
      <Rectangle
        x={x}
        y={y}
        width={width}
        height={height}
        fill={fill}
        fillOpacity={0.9}
      />
      <text
        textAnchor={isOut ? "end" : "start"}
        x={isOut ? x - 6 : x + width + 6}
        y={y + height / 2}
        fontSize={12}
        fill="#44403c"
        alignmentBaseline="middle"
      >
        {payload.name}
      </text>
      <text
        textAnchor={isOut ? "end" : "start"}
        x={isOut ? x - 6 : x + width + 6}
        y={y + height / 2 + 14}
        fontSize={10}
        fill="#a8a29e"
        alignmentBaseline="middle"
      >
        {payload.value} {payload.value === 1 ? "comment" : "comments"}
      </text>
    </Layer>
  );
}

export function GraphPage() {
  const [searchParams] = useSearchParams();
  const [docketId, setDocketId] = useState(() => searchParams.get("docket") ?? "");
  const [graph, setGraph] = useState<GraphResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);
  const [view, setView] = useState<View>("sankey");

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

  /** Convert the API's id-based graph into index-based Sankey data. */
  const sankeyData: SankeyDatum | null = useMemo(() => {
    if (!graph || graph.nodes.length === 0) return null;
    // Order: docket(s) first, then regulations sorted by count desc — gives a
    // tidy vertical stack on the right side of the diagram.
    const dockets = graph.nodes.filter((n) => n.type === "docket");
    const regulations = [...graph.nodes.filter((n) => n.type === "regulation")].sort(
      (a, b) => b.count - a.count,
    );
    const ordered = [...dockets, ...regulations];
    const indexById = new Map(ordered.map((n, i) => [n.id, i]));
    return {
      nodes: ordered.map((n) => ({
        name: n.label,
        type: n.type as "docket" | "regulation",
      })),
      links: graph.links
        .map((l) => ({
          source: indexById.get(l.source) ?? -1,
          target: indexById.get(l.target) ?? -1,
          value: l.value,
        }))
        .filter((l) => l.source >= 0 && l.target >= 0),
    };
  }, [graph]);

  const regulations = useMemo(
    () =>
      [...(graph?.nodes ?? [])]
        .filter((n) => n.type === "regulation")
        .sort((a, b) => b.count - a.count),
    [graph],
  );

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
          Wider flows = more comments cite that regulation.
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

      {sankeyData && (
        <>
          {/* legend + view switcher */}
          <div className="flex flex-wrap items-center justify-between gap-3 text-xs text-stone-600">
            <div className="flex flex-wrap gap-2">
              <span className="inline-flex items-center gap-2 rounded-full border border-stone-200 bg-white px-3 py-1 shadow-sm">
                <span className="h-2 w-2 rounded-full" style={{ background: DOCKET_COLOR }} />
                Docket
              </span>
              <span className="inline-flex items-center gap-2 rounded-full border border-stone-200 bg-white px-3 py-1 shadow-sm">
                <span className="h-2 w-2 rounded-full" style={{ background: REG_COLOR }} />
                Regulation
                <span className="text-stone-400">({regulations.length} unique)</span>
              </span>
            </div>
            <div className="inline-flex rounded-full border border-stone-200 bg-white p-0.5 shadow-sm">
              {(["sankey", "bars"] as const).map((v) => (
                <button
                  key={v}
                  type="button"
                  onClick={() => setView(v)}
                  className={`rounded-full px-3 py-1 text-xs font-medium transition ${
                    view === v
                      ? "bg-stone-900 text-stone-50"
                      : "text-stone-500 hover:text-stone-800"
                  }`}
                >
                  {v === "sankey" ? "Sankey" : "Bars"}
                </button>
              ))}
            </div>
          </div>

          {/* Sankey view */}
          {view === "sankey" && (
            <div className="overflow-hidden rounded-2xl border border-stone-200 bg-white p-3 shadow-sm">
              <ResponsiveContainer
                width="100%"
                height={Math.max(360, sankeyData.nodes.length * 36)}
              >
                <Sankey
                  data={sankeyData}
                  node={
                    (<SankeyNode x={0} y={0} width={0} height={0} payload={{ name: "" }} containerWidth={0} />) as unknown as React.ReactElement
                  }
                  nodePadding={22}
                  nodeWidth={14}
                  linkCurvature={0.5}
                  iterations={64}
                  link={{ stroke: "#d6d3d1", strokeOpacity: 0.4 }}
                >
                  <Tooltip
                    formatter={(value, _name, item) => {
                      const payload = (item as { payload?: LinkPayload | NodePayload } | undefined)?.payload;
                      if (payload && "source" in payload && typeof payload.source === "object") {
                        const link = payload as LinkPayload;
                        return [`${value} comments`, `${link.source.name} → ${link.target.name}`];
                      }
                      return [`${value} comments`, "total"];
                    }}
                    contentStyle={{
                      backgroundColor: "#ffffff",
                      border: "1px solid #e7e5e4",
                      borderRadius: 8,
                      fontSize: 12,
                      color: "#1c1917",
                      boxShadow: "0 4px 12px rgba(0,0,0,0.08)",
                    }}
                  />
                </Sankey>
              </ResponsiveContainer>
            </div>
          )}

          {/* Bar-chart view */}
          {view === "bars" && (
            <div className="overflow-hidden rounded-2xl border border-stone-200 bg-white p-5 shadow-sm">
              <ResponsiveContainer width="100%" height={Math.max(280, regulations.length * 32 + 40)}>
                <BarChart
                  data={regulations.map((r) => ({ name: r.label, count: r.count }))}
                  layout="vertical"
                  margin={{ top: 4, right: 24, left: 8, bottom: 4 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#e7e5e4" horizontal={false} />
                  <XAxis type="number" tick={{ fontSize: 11, fill: "#78716c" }} stroke="#d6d3d1" />
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
                    cursor={{ fill: "rgba(16,185,129,0.08)" }}
                  />
                  <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                    {regulations.map((r) => (
                      <Cell key={r.id} fill={REG_COLOR} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Top cited list (kept below either view for at-a-glance totals) */}
          <section className="space-y-3">
            <h2 className="text-xs font-semibold uppercase tracking-widest text-amber-600">
              Top cited regulations
            </h2>
            <div className="overflow-hidden rounded-2xl border border-stone-200 bg-white shadow-sm">
              {regulations.slice(0, 10).map((n, i, arr) => (
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
