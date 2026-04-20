import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getDockets } from "../api/client";
import type { DocketSummary } from "../types/api";

export function HomePage() {
  const [topDockets, setTopDockets] = useState<DocketSummary[]>([]);

  useEffect(() => {
    getDockets(undefined, 5)
      .then(setTopDockets)
      .catch(() => setTopDockets([]));
  }, []);

  return (
    <div className="p-6 space-y-8">
      <section className="space-y-2">
        <h1 className="text-3xl font-bold">RegScope</h1>
        <p className="text-slate-700">
          Regulatory intelligence — astroturf detection and comment clustering
          for federal rulemaking.
        </p>
      </section>

      {/* Feature cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Link
          to="/astroturf"
          className="rounded-lg border border-slate-200 bg-white p-6 hover:bg-slate-50 transition"
        >
          <div className="text-xl font-semibold">Astroturf Detector</div>
          <p className="mt-2 text-slate-600">
            Identify duplicate comment campaigns and template-driven submissions.
          </p>
        </Link>
        <Link
          to="/clusters"
          className="rounded-lg border border-slate-200 bg-white p-6 hover:bg-slate-50 transition"
        >
          <div className="text-xl font-semibold">Comment Clusters</div>
          <p className="mt-2 text-slate-600">
            Explore topic clusters within a docket, labeled by AI.
          </p>
        </Link>
        <Link
          to="/graph"
          className="rounded-lg border border-slate-200 bg-white p-6 hover:bg-slate-50 transition"
        >
          <div className="text-xl font-semibold">Citation Graph</div>
          <p className="mt-2 text-slate-600">
            Visualize which CFR and U.S.C. regulations a docket&apos;s comments
            reference most.
          </p>
        </Link>
        <Link
          to="/query"
          className="rounded-lg border border-slate-200 bg-white p-6 hover:bg-slate-50 transition"
        >
          <div className="text-xl font-semibold">Ask a Question</div>
          <p className="mt-2 text-slate-600">
            Ask anything in plain English — RAG retrieves the most relevant
            comments and GPT-4o-mini synthesises an answer.
          </p>
        </Link>
      </div>

      {/* Live top-dockets section (only rendered once data is available) */}
      {topDockets.length > 0 && (
        <section className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold">Available dockets</h2>
            <Link
              to="/dockets"
              className="text-sm text-blue-600 hover:underline"
            >
              Browse all →
            </Link>
          </div>
          <ul className="space-y-2">
            {topDockets.map((d) => (
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
        </section>
      )}
    </div>
  );
}
