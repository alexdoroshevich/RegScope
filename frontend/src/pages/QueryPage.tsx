import { useCallback, useState } from "react";
import { postQuery } from "../api/client";
import type { QueryResponse, SourceComment } from "../types/api";

function SourceCard({ src, index }: { src: SourceComment; index: number }) {
  const [expanded, setExpanded] = useState(false);
  const preview = src.comment_text.slice(0, 200);
  const hasMore = src.comment_text.length > 200;

  return (
    <li className="rounded-lg border border-slate-200 bg-white p-4 text-sm space-y-1">
      <div className="flex items-center justify-between">
        <span className="font-medium text-slate-700">
          [{index}] {src.comment_id}
        </span>
        <span className="text-xs text-slate-400">
          similarity {(src.similarity * 100).toFixed(1)}%
        </span>
      </div>
      <p className="text-slate-600">
        {expanded ? src.comment_text : preview}
        {!expanded && hasMore && "…"}
      </p>
      {hasMore && (
        <button
          onClick={() => setExpanded((v) => !v)}
          className="text-blue-600 text-xs hover:underline"
        >
          {expanded ? "Show less" : "Show more"}
        </button>
      )}
    </li>
  );
}

export function QueryPage() {
  const [docketId, setDocketId] = useState("");
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<QueryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = useCallback(async () => {
    if (!docketId.trim() || !question.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await postQuery(docketId.trim(), question.trim());
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, [docketId, question]);

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-3xl font-bold">Ask a Question</h1>
      <p className="text-slate-600 text-sm">
        Ask anything about a docket&apos;s public comments. The most relevant comments
        are retrieved and GPT-4o-mini synthesises an answer from them.
      </p>

      <form
        className="space-y-3"
        onSubmit={(e) => {
          e.preventDefault();
          void submit();
        }}
      >
        <input
          type="text"
          value={docketId}
          onChange={(e) => setDocketId(e.target.value)}
          placeholder="Docket ID (e.g. EPA-HQ-OAR-2021-0317)"
          className="w-full rounded-lg border border-slate-300 px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <div className="flex gap-3">
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="What concerns do commenters raise about small businesses?"
            className="flex-1 rounded-lg border border-slate-300 px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            type="submit"
            disabled={loading || !docketId.trim() || !question.trim()}
            className="rounded-lg bg-blue-600 px-6 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? "Thinking…" : "Ask"}
          </button>
        </div>
      </form>

      {error && <div className="text-red-700 text-sm">Error: {error}</div>}

      {result && (
        <div className="space-y-6">
          {/* Answer */}
          <section className="rounded-lg border border-blue-200 bg-blue-50 p-5 space-y-2">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-blue-900">Answer</h2>
              <div className="flex items-center gap-3 text-xs text-blue-600">
                {result.from_cache && (
                  <span className="rounded bg-blue-100 px-2 py-0.5">cached</span>
                )}
                <span>{result.model}</span>
                {result.cost_usd > 0 && (
                  <span>${result.cost_usd.toFixed(5)}</span>
                )}
              </div>
            </div>
            <p className="text-slate-800 text-sm leading-relaxed whitespace-pre-wrap">
              {result.answer}
            </p>
          </section>

          {/* Sources */}
          {result.sources.length > 0 && (
            <section>
              <h2 className="text-lg font-semibold mb-3">
                Source comments ({result.sources.length})
              </h2>
              <ul className="space-y-3">
                {result.sources.map((src, i) => (
                  <SourceCard key={src.comment_id} src={src} index={i + 1} />
                ))}
              </ul>
            </section>
          )}
        </div>
      )}
    </div>
  );
}
