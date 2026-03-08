import { useState } from "react";
import "./App.css";

import { useSearch } from "./hooks/useSearch";
import StatusBar from "./components/StatusBar";
import DataTable from "./components/DataTable";
import HeaderGenerator from "./components/HeaderGenerator";

const DEFAULT_ACTIVE = ["name", "rating", "reviews", "address", "phone", "website", "category", "source_url"];

export default function App() {
  const { query, setQuery, results, status, loading, error, handleSearch, handleClear } =
    useSearch();
  const [activeHeaders, setActiveHeaders] = useState(DEFAULT_ACTIVE);

  const onKeyDown = (e) => { if (e.key === "Enter" && !loading) handleSearch(); };

  const toggleHeader = (key) =>
    setActiveHeaders((prev) =>
      prev.includes(key) ? prev.filter((h) => h !== key) : [...prev, key]
    );

  return (
    <div className="app-layout">
      {/* ── Header ── */}
      <header className="app-header">
        <h1>Google Maps AI Agent</h1>
        <div className="subtitle">Doğal dilde arama yap — AI senin için listelesin</div>
      </header>

      {/* ── Search ── */}
      <section className="search-section">
        <div className="search-container">
          <div className="search-input-wrapper">
            <span className="search-icon">🔍</span>
            <input
              className="search-input"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder="Örn: Kadıköy kahveci"
              disabled={loading}
              autoFocus
            />
            <button
              className="search-btn"
              onClick={handleSearch}
              disabled={loading || !query.trim()}
            >
              {loading ? <span className="spinner" /> : null}
              {loading ? "Aranıyor..." : "Ara →"}
            </button>
          </div>
          {(results.length > 0 || query) && (
            <button className="clear-btn" onClick={handleClear} disabled={loading}>
              ✕
            </button>
          )}
        </div>

        <div className="status-wrapper">
          <StatusBar status={status} />
          {error && <div className="error-message" style={{ color: "var(--error)", marginTop: "10px" }}>⚠ {error}</div>}
        </div>
      </section>

      {/* ── Data Panel ── */}
      <div className="data-panel">
        <div className="data-table-container">
          <HeaderGenerator
            query={query}
            results={results}
            activeHeaders={activeHeaders}
            onToggle={toggleHeader}
          />
        </div>
        <DataTable results={results} activeHeaders={activeHeaders} />
      </div>
    </div>
  );
}
