import { useCallback, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { postQuery } from "../api/client";
import { DocketSearch } from "../components/DocketSearch";
import type { QueryResponse, SourceComment } from "../types/api";

function SourceCard({ src, index }: { src: SourceComment; index: number }) {
  const [expanded, setExpanded] = useState(false);
  const preview = src.comment_text.slice(0, 220);
  const hasMore = src.comment_text.length > 220;
  const similarityPct = (src.similarity * 100).toFixed(1);

  return (
    <li className="rounded-2xl border border-stone-200 bg-white p-4 text-sm shadow-sm transition hover:border-stone-300">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-md bg-rose-100 text-xs font-bold text-rose-700">
            {index}
          </span>
          <span className="font-mono text-xs text-stone-500">{src.comment_id}</span>
        </div>
        <span className="shrink-0 rounded-full border border-stone-200 bg-stone-50 px-2 py-0.5 text-xs tabular-nums text-stone-600">
          {similarityPct}% match
        </span>
      </div>
      <p className="mt-3 whitespace-pre-wrap text-stone-700">
        {expanded ? src.comment_text : preview}
        {!expanded && hasMore && "…"}
      </p>
      {hasMore && (
        <button
          onClick={() => setExpanded((v) => !v)}
          className="mt-2 text-xs font-medium text-rose-600 transition hover:text-rose-700"
        >
          {expanded ? "Show less" : "Show more"}
        </button>
      )}
    </li>
  );
}

export function QueryPage() {
  const [searchParams] = useSearchParams();
  const [docketId, setDocketId] = useState(() => searchParams.get("docket") ?? "");
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
    <div className="space-y-8">
      {/* header */}
      <div>
        <div className="flex items-center gap-2">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-rose-100 text-rose-600 ring-1 ring-rose-200">
            ⊕
          </span>
          <h1 className="text-2xl font-bold text-stone-800">Ask a Question</h1>
        </div>
        <p className="mt-1 max-w-2xl text-sm text-stone-500">
          Plain-English RAG over public comments — the most relevant comments are
          retrieved and the answer is synthesised with GPT-4o-mini.
        </p>
      </div>

      {/* form */}
      <form
        className="space-y-3"
        onSubmit={(e) => {
          e.preventDefault();
          void submit();
        }}
      >
        <DocketSearch
          value={docketId}
          onChange={setDocketId}
          placeholder="Docket ID (e.g. EPA-HQ-OAR-2021-0317)"
          className="w-full"
        />
        <div className="flex gap-3">
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="What concerns do commenters raise about small businesses?"
            className="flex-1 rounded-lg border border-stone-300 bg-white px-4 py-2 text-sm text-stone-900 placeholder-stone-400 shadow-sm transition focus:border-amber-500 focus:outline-none focus:ring-1 focus:ring-amber-500"
          />
          <button
            type="submit"
            disabled={loading || !docketId.trim() || !question.trim()}
            className="rounded-lg bg-gradient-to-r from-amber-500 to-rose-500 px-5 py-2 text-sm font-semibold text-white shadow-sm transition hover:shadow-md disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? "Thinking…" : "Ask"}
          </button>
        </div>
      </form>

      {error && (
        <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {error}
        </div>
      )}

      {result && (
        <div className="space-y-6">
          {/* Answer */}
          <section className="rounded-2xl border border-rose-200 bg-gradient-to-br from-rose-50 via-white to-amber-50 p-5 shadow-sm">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="flex h-6 w-6 items-center justify-center rounded-md bg-rose-100 text-rose-700">
                  ◆
                </span>
                <h2 className="text-sm font-semibold text-stone-800">Answer</h2>
              </div>
              <div className="flex items-center gap-2 text-xs">
                {result.from_cache && (
                  <span className="rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 font-medium text-emerald-700">
                    cached
                  </span>
                )}
                <span className="rounded-full border border-stone-200 bg-white px-2 py-0.5 font-mono text-stone-600">
                  {result.model}
                </span>
                {result.cost_usd > 0 && (
                  <span className="rounded-full border border-stone-200 bg-white px-2 py-0.5 tabular-nums text-stone-600">
                    ${result.cost_usd.toFixed(5)}
                  </span>
                )}
              </div>
            </div>
            <p className="mt-4 whitespace-pre-wrap text-sm leading-relaxed text-stone-700">
              {result.answer}
            </p>
          </section>

          {/* Sources */}
          {result.sources.length > 0 && (
            <section className="space-y-3">
              <h2 className="text-xs font-semibold uppercase tracking-widest text-amber-600">
                Evidence · {result.sources.length} source comments
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
