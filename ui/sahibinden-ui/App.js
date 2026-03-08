import React, { useState } from "react";
import "./App.css";
import SearchBox from "./components/SearchBox";
import ResultsTable from "./components/ResultsTable";
import ScrollToTop from "./components/ScrollToTop";

function App() {
    const [results, setResults] = useState([]);
    const [headers, setHeaders] = useState([]);

    return (
        <div>
            {/* Hero / Search Section */}
            <section className="hero">
                <h1 className="hero-title">Sahibinden AI Agent</h1>
                <p className="hero-subtitle">
                    Doğal dilde arama yap — AI senin için listelesin
                </p>
                <SearchBox
                    setResults={setResults}
                    setHeaders={setHeaders}
                />
            </section>

            {/* Results Section */}
            <section className="results-section">
                <ResultsTable data={results} headers={headers} />
            </section>

            {/* Scroll to Top Button */}
            <ScrollToTop />
        </div >
    );
}

export default App;