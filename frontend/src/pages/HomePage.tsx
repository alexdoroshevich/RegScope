import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getDockets } from "../api/client";
import type { DocketSummary } from "../types/api";

const features = [
  {
    to: "/astroturf",
    title: "Astroturf Detector",
    tagline: "Find coordinated campaigns.",
    description:
      "MinHash + LSH deduplication surfaces near-identical submissions and templates — the fingerprint of an organised campaign.",
    wash: "from-orange-100/80 via-transparent to-transparent",
    chip: "bg-orange-100 text-orange-700 ring-orange-200/70",
    glow: "shadow-[0_24px_80px_-32px_rgba(234,88,12,0.35)]",
    icon: "⚡",
    tag: "Feature",
  },
  {
    to: "/clusters",
    title: "Comment Clusters",
    tagline: "Topics, not keywords.",
    description:
      "Sentence embeddings → HDBSCAN → GPT-4o-mini labels. Understand what people actually said, grouped by meaning.",
    wash: "from-sky-100/70 via-transparent to-transparent",
    chip: "bg-sky-100 text-sky-700 ring-sky-200/70",
    glow: "shadow-[0_24px_80px_-32px_rgba(14,165,233,0.35)]",
    icon: "◎",
    tag: "Feature",
  },
  {
    to: "/graph",
    title: "Citation Graph",
    tagline: "Where regulations intersect.",
    description:
      "Extracts CFR and U.S.C. references across a docket's comments and maps them as a citation network.",
    wash: "from-emerald-100/70 via-transparent to-transparent",
    chip: "bg-emerald-100 text-emerald-700 ring-emerald-200/70",
    glow: "shadow-[0_24px_80px_-32px_rgba(16,185,129,0.35)]",
    icon: "⬡",
    tag: "Phase 2",
  },
  {
    to: "/query",
    title: "Ask a Question",
    tagline: "Plain English, grounded answers.",
    description:
      "Retrieval-augmented generation over public comments. Every answer cites the source submissions it drew from.",
    wash: "from-rose-100/70 via-transparent to-transparent",
    chip: "bg-rose-100 text-rose-700 ring-rose-200/70",
    glow: "shadow-[0_24px_80px_-32px_rgba(244,63,94,0.35)]",
    icon: "⊕",
    tag: "Phase 2",
  },
];

const howItWorks = [
  {
    step: "01",
    title: "Pick a docket",
    body: "Browse or search dockets ingested from the Federal Register and Regulations.gov.",
  },
  {
    step: "02",
    title: "See the signal",
    body: "Campaign likelihood, topic clusters, and regulatory citations — computed, not guessed.",
  },
  {
    step: "03",
    title: "Ask anything",
    body: "A plain-English question returns an answer grounded in the comments it cites.",
  },
];

export function HomePage() {
  const [topDockets, setTopDockets] = useState<DocketSummary[]>([]);

  useEffect(() => {
    getDockets(undefined, 5)
      .then((resp) => setTopDockets(resp.items))
      .catch(() => setTopDockets([]));
  }, []);

  return (
    <div className="-mx-6 -my-8">
      {/* ── HERO ────────────────────────────────────────────── */}
      <section className="relative overflow-hidden px-6 pt-24 pb-32 sm:pt-32 sm:pb-40">
        {/* warm ambient gradient */}
        <div
          aria-hidden
          className="pointer-events-none absolute inset-x-0 top-0 -z-10 flex justify-center"
        >
          <div className="h-[44rem] w-[72rem] -translate-y-1/3 rounded-full bg-[radial-gradient(closest-side,rgba(251,191,36,0.28),rgba(251,146,60,0.14)_35%,rgba(244,63,94,0.06)_60%,transparent_80%)] blur-2xl" />
        </div>

        <div className="mx-auto max-w-4xl text-center">
          <div className="inline-flex items-center gap-2 rounded-full border border-stone-200 bg-white/80 px-3 py-1 text-xs font-medium text-stone-700 shadow-sm backdrop-blur">
            <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
            Open-source · Federal Register · AI-powered
          </div>

          <h1 className="mt-8 text-5xl font-bold leading-[1.05] tracking-tighter text-stone-600 sm:text-7xl">
            Regulatory intelligence,
            <br />
            <span className="text-gradient">automated.</span>
          </h1>

          <p className="mx-auto mt-6 max-w-2xl text-base text-stone-600 sm:text-lg">
            Analyse public comments on federal regulations to detect astroturf
            campaigns, cluster comments by topic, and map cross-rule impact —
            at scale.
          </p>

          <div className="mt-10 flex flex-wrap items-center justify-center gap-3">
            <Link
              to="/dockets"
              className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-amber-500 to-rose-500 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:shadow-md"
            >
              Browse dockets
              <span aria-hidden>→</span>
            </Link>
            <Link
              to="/astroturf"
              className="inline-flex items-center gap-2 rounded-full border border-stone-300 bg-white px-5 py-2.5 text-sm font-medium text-stone-800 transition hover:border-stone-400 hover:bg-stone-100"
            >
              See detections
            </Link>
          </div>

          {/* trust row */}
          <div className="mt-14 flex flex-wrap items-center justify-center gap-x-8 gap-y-3 text-xs text-stone-500">
            <span>Federal Register API</span>
            <span className="h-1 w-1 rounded-full bg-stone-300" />
            <span>Regulations.gov</span>
            <span className="h-1 w-1 rounded-full bg-stone-300" />
            <span>DuckDB · Polars · FastAPI</span>
            <span className="h-1 w-1 rounded-full bg-stone-300" />
            <span>Apache 2.0</span>
          </div>
        </div>
      </section>

      {/* ── CAPABILITIES ────────────────────────────────────── */}
      <section className="border-t border-stone-200/70 px-6 py-24 sm:py-32">
        <div className="mx-auto max-w-6xl">
          <div className="mb-12 text-center">
            <div className="text-xs font-semibold uppercase tracking-widest text-amber-600">
              Capabilities
            </div>
            <h2 className="mt-3 text-3xl font-bold tracking-tight text-stone-900 sm:text-5xl">
              Four lenses on the same data.
            </h2>
            <p className="mx-auto mt-4 max-w-2xl text-sm text-stone-600 sm:text-base">
              Every view starts with the same raw public comments — and ends
              somewhere different.
            </p>
          </div>

          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
            {features.map((f) => (
              <Link
                key={f.to}
                to={f.to}
                className={`group relative overflow-hidden rounded-3xl border border-stone-200 bg-white p-8 transition hover:border-stone-300 hover:-translate-y-0.5 ${f.glow}`}
              >
                {/* accent wash */}
                <div
                  aria-hidden
                  className={`pointer-events-none absolute inset-0 bg-gradient-to-br ${f.wash}`}
                />

                <div className="relative flex items-start justify-between">
                  <span
                    className={`inline-flex h-10 w-10 items-center justify-center rounded-xl text-lg ring-1 ${f.chip}`}
                  >
                    {f.icon}
                  </span>
                  <span className="rounded-full border border-stone-200 bg-white/80 px-2.5 py-0.5 text-[10px] font-medium uppercase tracking-wider text-stone-500">
                    {f.tag}
                  </span>
                </div>

                <div className="relative mt-6">
                  <h3 className="text-lg font-semibold tracking-tight text-stone-900">
                    {f.title}
                  </h3>
                  <p className="mt-1 text-sm font-medium text-stone-700">
                    {f.tagline}
                  </p>
                  <p className="mt-4 text-sm leading-relaxed text-stone-600">
                    {f.description}
                  </p>
                </div>

                <div className="relative mt-8 inline-flex items-center gap-1 text-xs font-medium text-stone-500 transition group-hover:text-amber-600">
                  Explore
                  <span
                    className="transition group-hover:translate-x-0.5"
                    aria-hidden
                  >
                    →
                  </span>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* ── HOW IT WORKS ───────────────────────────────────── */}
      <section className="border-t border-stone-200/70 bg-gradient-to-b from-stone-50 via-amber-50/30 to-stone-50 px-6 py-24 sm:py-32">
        <div className="mx-auto max-w-5xl">
          <div className="mb-12 text-center">
            <div className="text-xs font-semibold uppercase tracking-widest text-amber-600">
              How it works
            </div>
            <h2 className="mt-3 text-3xl font-bold tracking-tight text-stone-900 sm:text-5xl">
              Three steps, no setup.
            </h2>
          </div>

          <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
            {howItWorks.map((s) => (
              <div
                key={s.step}
                className="rounded-2xl border border-stone-200 bg-white p-6 shadow-sm transition hover:shadow-md"
              >
                <div className="font-mono text-xs tracking-widest text-amber-600">
                  {s.step}
                </div>
                <div className="mt-3 text-lg font-semibold tracking-tight text-stone-900">
                  {s.title}
                </div>
                <p className="mt-2 text-sm leading-relaxed text-stone-600">
                  {s.body}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── PURPOSE & SCOPE (legal cover) ──────────────────── */}
      <section className="border-t border-stone-200/70 px-6 py-20">
        <div className="mx-auto grid max-w-5xl gap-10 md:grid-cols-2">
          <div>
            <div className="text-xs font-semibold uppercase tracking-widest text-amber-600">
              What it is
            </div>
            <h3 className="mt-3 text-2xl font-bold tracking-tight text-stone-900">
              A research tool, open to everyone.
            </h3>
            <p className="mt-4 text-sm leading-relaxed text-stone-600">
              An open-source analysis tool for public comments submitted on US
              federal regulations. The goal is to surface patterns —
              coordinated campaigns, shared concerns, regulatory overlap — that
              would be invisible in a linear read of thousands of individual
              submissions.
            </p>
          </div>
          <div>
            <div className="text-xs font-semibold uppercase tracking-widest text-stone-500">
              What it isn&apos;t
            </div>
            <h3 className="mt-3 text-2xl font-bold tracking-tight text-stone-800">
              Not advice, not official.
            </h3>
            <ul className="mt-4 space-y-2 text-sm leading-relaxed text-stone-600">
              <li className="flex gap-2">
                <span className="text-stone-400" aria-hidden>
                  •
                </span>
                Not legal, regulatory, or professional advice.
              </li>
              <li className="flex gap-2">
                <span className="text-stone-400" aria-hidden>
                  •
                </span>
                Not affiliated with any US government agency.
              </li>
              <li className="flex gap-2">
                <span className="text-stone-400" aria-hidden>
                  •
                </span>
                AI-generated summaries and labels may be inaccurate — verify
                before relying on them.
              </li>
              <li className="flex gap-2">
                <span className="text-stone-400" aria-hidden>
                  •
                </span>
                Provided &ldquo;as is&rdquo; under the Apache 2.0 licence.
              </li>
            </ul>
          </div>
        </div>
      </section>

      {/* ── RECENT DOCKETS ─────────────────────────────────── */}
      {topDockets.length > 0 && (
        <section className="border-t border-stone-200/70 px-6 py-20">
          <div className="mx-auto max-w-5xl">
            <div className="mb-6 flex items-end justify-between">
              <div>
                <div className="text-xs font-semibold uppercase tracking-widest text-amber-600">
                  Live data
                </div>
                <h2 className="mt-2 text-2xl font-bold tracking-tight text-stone-900 sm:text-3xl">
                  Recent dockets
                </h2>
              </div>
              <Link
                to="/dockets"
                className="text-sm text-stone-600 transition hover:text-amber-600"
              >
                View all →
              </Link>
            </div>
            <div className="overflow-hidden rounded-2xl border border-stone-200 bg-white shadow-sm">
              {topDockets.map((d, i) => (
                <div
                  key={d.docket_id}
                  className={`flex flex-col items-start justify-between gap-3 px-5 py-4 transition hover:bg-stone-50 sm:flex-row sm:items-center ${
                    i !== topDockets.length - 1
                      ? "border-b border-stone-200/70"
                      : ""
                  }`}
                >
                  <div>
                    <span className="font-mono text-sm font-medium text-stone-900">
                      {d.docket_id}
                    </span>
                    <span className="ml-3 text-xs text-stone-500">
                      {d.comment_count.toLocaleString()} comments
                    </span>
                  </div>
                  <div className="flex gap-2">
                    {[
                      { to: `/clusters?docket=${encodeURIComponent(d.docket_id)}`, label: "Clusters" },
                      { to: `/graph?docket=${encodeURIComponent(d.docket_id)}`, label: "Graph" },
                      { to: `/query?docket=${encodeURIComponent(d.docket_id)}`, label: "Ask" },
                    ].map((a) => (
                      <Link
                        key={a.label}
                        to={a.to}
                        className="rounded-full border border-stone-200 bg-white px-3 py-1 text-xs text-stone-700 transition hover:border-stone-300 hover:bg-stone-100"
                      >
                        {a.label}
                      </Link>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* ── EMPTY STATE ────────────────────────────────────── */}
      {topDockets.length === 0 && (
        <section className="border-t border-stone-200/70 px-6 py-20">
          <div className="mx-auto max-w-2xl rounded-2xl border border-stone-200 bg-white p-10 text-center shadow-sm">
            <div className="inline-flex h-10 w-10 items-center justify-center rounded-xl bg-amber-100 text-amber-700">
              ∅
            </div>
            <p className="mt-4 text-base font-medium text-stone-900">
              No dockets ingested yet
            </p>
            <p className="mt-2 text-sm text-stone-600">
              Run the ingestion pipeline to pull data from Regulations.gov, then
              come back to explore.
            </p>
            <Link
              to="/dockets"
              className="mt-6 inline-flex items-center gap-1.5 rounded-full border border-stone-300 bg-white px-4 py-2 text-xs font-medium text-stone-800 transition hover:bg-stone-100"
            >
              Go to Dockets
            </Link>
          </div>
        </section>
      )}

      {/* ── DISCLAIMER FOOTER ──────────────────────────────── */}
      <footer className="border-t border-stone-200/70 bg-stone-100 px-6 py-12">
        <div className="mx-auto max-w-5xl">
          <p className="text-xs leading-relaxed text-stone-500">
            This site is a research and educational tool. It is not legal,
            regulatory, or professional advice, and is not affiliated with,
            endorsed by, or sponsored by any US government agency. AI-generated
            summaries, labels, and answers may contain errors. Data is sourced
            from public US federal APIs; submitter information is derived from
            public-record comments and is anonymised by default. Provided
            &ldquo;as is&rdquo; under the Apache 2.0 licence with no warranty.
            By using this site you accept full responsibility for any decisions
            you make based on its output.
          </p>
        </div>
      </footer>
    </div>
  );
}
