import { Link } from "react-router-dom";

export function HomePage() {
  return (
    <div className="p-6 space-y-6">
      <h1 className="text-3xl font-bold">RegScope</h1>
      <p className="text-slate-700">
        Regulatory intelligence — astroturf detection and comment clustering for
        federal rulemaking.
      </p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Link
          to="/astroturf"
          className="rounded-lg border border-slate-200 bg-white p-6 hover:bg-slate-50 transition"
        >
          <div className="text-xl font-semibold">Astroturf Detector</div>
          <p className="mt-2 text-slate-600">
            Identify duplicate comment campaigns and template-driven submissions.
          </p>
        </Link>
      </div>
    </div>
  );
}
