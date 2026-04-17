import { Link, Route, Routes } from "react-router-dom";
import { AstroturfPage } from "./pages/AstroturfPage";
import { HomePage } from "./pages/HomePage";

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
        </nav>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/astroturf" element={<AstroturfPage />} />
        </Routes>
      </main>
    </div>
  );
}
