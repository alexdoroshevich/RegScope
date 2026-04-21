import { Component, lazy, Suspense } from "react";
import type { ErrorInfo, ReactNode } from "react";
import { NavLink, Route, Routes } from "react-router-dom";
import { AstroturfPage } from "./pages/AstroturfPage";
import { ClustersPage } from "./pages/ClustersPage";
import { DocketsPage } from "./pages/DocketsPage";
import { HomePage } from "./pages/HomePage";
import { QueryPage } from "./pages/QueryPage";

// GraphPage renders a Recharts Sankey + optional bar chart. Lazy-load it
// so any rendering failure (e.g. data-shape mismatch) falls back
// gracefully instead of taking down the rest of the app. Map the named
// export to `default` to satisfy React.lazy's contract.
const GraphPage = lazy(() =>
  import("./pages/GraphPage")
    .then((mod) => ({ default: mod.GraphPage }))
    .catch(() => ({
      default: () => (
        <div className="space-y-4">
          <h1 className="text-3xl font-bold text-stone-900">Citation Graph</h1>
          <div className="rounded-xl border border-stone-200 bg-white p-6 text-sm text-stone-600">
            Graph visualisation failed to load. See the browser console
            for details.
          </div>
        </div>
      ),
    })),
);

// Minimal error boundary so a runtime error inside GraphPage doesn't
// propagate and blank the whole layout.
interface EBState {
  caught: boolean;
}
class GraphErrorBoundary extends Component<
  { children: ReactNode },
  EBState
> {
  state: EBState = { caught: false };
  componentDidCatch(_err: Error, _info: ErrorInfo) {
    this.setState({ caught: true });
  }
  render() {
    if (this.state.caught) {
      return (
        <div className="space-y-4">
          <h1 className="text-3xl font-bold text-stone-900">Citation Graph</h1>
          <div className="rounded-xl border border-stone-200 bg-white p-6 text-sm text-stone-600">
            Graph visualisation crashed at runtime. Check the browser console for
            details.
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

const navItems = [
  { to: "/dockets", label: "Dockets" },
  { to: "/astroturf", label: "Astroturf" },
  { to: "/clusters", label: "Clusters" },
  { to: "/graph", label: "Citation Graph" },
  { to: "/query", label: "Ask" },
];

export default function App() {
  return (
    <div className="min-h-screen bg-stone-50 text-stone-900">
      {/* ── top nav ── */}
      <header className="sticky top-0 z-50 border-b border-stone-200/70 bg-stone-50/80 backdrop-blur-md">
        <nav className="mx-auto flex max-w-7xl items-center gap-2 px-6 py-3">
          {/* brand */}
          <NavLink
            to="/"
            className="mr-4 flex items-center gap-2 text-sm font-semibold text-stone-900"
          >
            <span className="flex h-6 w-6 items-center justify-center rounded-md bg-gradient-to-br from-amber-500 to-rose-500 text-xs font-bold text-white shadow-sm">
              F
            </span>
            FedComment
          </NavLink>

          {/* links */}
          {navItems.map(({ to, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `rounded-md px-3 py-1.5 text-sm transition-colors ${
                  isActive
                    ? "bg-stone-200/80 text-stone-800 font-medium"
                    : "text-stone-500 hover:bg-stone-100 hover:text-stone-800"
                }`
              }
            >
              {label}
            </NavLink>
          ))}
        </nav>
      </header>

      {/* ── content ── */}
      <main className="mx-auto max-w-7xl px-6 py-8">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/dockets" element={<DocketsPage />} />
          <Route path="/astroturf" element={<AstroturfPage />} />
          <Route path="/clusters" element={<ClustersPage />} />
          <Route
            path="/graph"
            element={
              <GraphErrorBoundary>
                <Suspense
                  fallback={
                    <div className="text-sm text-zinc-500">
                      Loading graph…
                    </div>
                  }
                >
                  <GraphPage />
                </Suspense>
              </GraphErrorBoundary>
            }
          />
          <Route path="/query" element={<QueryPage />} />
        </Routes>
      </main>
    </div>
  );
}
