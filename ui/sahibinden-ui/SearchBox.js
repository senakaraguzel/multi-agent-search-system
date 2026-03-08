import React, { useState } from "react";
import { searchListings } from "../services/api";

function SearchBox({ setResults, setHeaders }) {
    const [query, setQuery] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const handleSearch = async () => {
        if (!query.trim()) {
            setError("Lütfen bir arama sorgusu girin.");
            return;
        }
        setError(null);
        setLoading(true);
        setResults([]);
        setHeaders([]);

        try {
            const { data, headers } = await searchListings(query);
            setResults(data);
            setHeaders(headers);
        } catch (err) {
            setError(err.message || "Bir hata oluştu.");
        } finally {
            setLoading(false);
        }
    };

    const handleKeyDown = (e) => {
        if (e.key === "Enter") handleSearch();
    };

    return (
        <>
            <div className="search-container">
                <span style={{ fontSize: 18 }}>🔍</span>
                <input
                    id="search-input"
                    className="search-input"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder='Örn: Kadıköy 3+1 kiralık ev'
                    autoComplete="off"
                />
                <button
                    id="search-button"
                    className="search-button"
                    onClick={handleSearch}
                    disabled={loading}
                >
                    {loading ? (
                        <span>
                            <span className="spinner" />
                            <span>Aranıyor...</span>
                        </span>
                    ) : (
                        <span>Ara →</span>
                    )}
                </button>
            </div>

            <div className="status-bar">
                {error && (
                    <div className="msg-error">
                        <span>⚠️ {error}</span>
                    </div>
                )}
                {loading && (
                    <div className="msg-loading">
                        <span className="spinner" />
                        <span>AI agentlar çalışıyor, lütfen bekleyin (1-2 dakika sürebilir)...</span>
                    </div>
                )}
            </div>
        </>
    );
}

export default SearchBox;