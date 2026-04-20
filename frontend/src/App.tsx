import { Link, Route, Routes } from "react-router-dom";
import { AstroturfPage } from "./pages/AstroturfPage";
import { ClustersPage } from "./pages/ClustersPage";
import { GraphPage } from "./pages/GraphPage";
import { HomePage } from "./pages/HomePage";
import { QueryPage } from "./pages/QueryPage";

export default function App() {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <nav className="px-6 py-3 flex gap-4">
          <Link to="/" className="font-semibold">
            RegScope
          </Link>
          <Link to="/astroturf" className="text-slate-600 hover:text-slate-900">
            Astroturf
          </Link>
          <Link to="/clusters" className="text-slate-600 hover:text-slate-900">
            Clusters
          </Link>
          <Link to="/graph" className="text-slate-600 hover:text-slate-900">
            Citation Graph
          </Link>
          <Link to="/query" className="text-slate-600 hover:text-slate-900">
            Ask a Question
          </Link>
        </nav>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/astroturf" element={<AstroturfPage />} />
          <Route path="/clusters" element={<ClustersPage />} />
          <Route path="/graph" element={<GraphPage />} />
          <Route path="/query" element={<QueryPage />} />
        </Routes>
      </main>
    </div>
  );
}
