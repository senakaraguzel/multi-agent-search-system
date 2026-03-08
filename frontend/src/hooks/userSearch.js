import { useState, useEffect, useCallback, useRef } from "react";
import { fetchResults, fetchStatus, startSearch, clearResults } from "../api";

export function useSearch() {
    const [query, setQuery] = useState("");
    const [results, setResults] = useState([]);
    const [status, setStatus] = useState({ phase: "idle", running: false, urls_found: 0, results_count: 0, error: null, query: "" });
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const pollRef = useRef(null);

    // Mevcut sonuçları yükle
    const loadResults = useCallback(async () => {
        try {
            const data = await fetchResults();
            setResults(data.results || []);
        } catch (e) {
            console.error("Sonuç yükleme hatası:", e);
        }
    }, []);

    // İlk yüklemede mevcut sonuçları getir
    useEffect(() => {
        loadResults();
        fetchStatus().then(setStatus).catch(console.error);
    }, [loadResults]);

    // Polling — scraper çalışırken status + results güncelle
    const startPolling = useCallback(() => {
        if (pollRef.current) return;
        pollRef.current = setInterval(async () => {
            try {
                const s = await fetchStatus();
                setStatus(s);
                if (s.phase === "extracting" || s.phase === "done") {
                    const data = await fetchResults();
                    setResults(data.results || []);
                }
                if (!s.running && (s.phase === "done" || s.phase === "error" || s.phase === "idle")) {
                    stopPolling();
                    setLoading(false);
                    if (s.phase === "done") {
                        const data = await fetchResults();
                        setResults(data.results || []);
                    }
                }
            } catch (e) {
                console.error("Polling hatası:", e);
            }
        }, 2000);
    }, []);

    const stopPolling = useCallback(() => {
        if (pollRef.current) {
            clearInterval(pollRef.current);
            pollRef.current = null;
        }
    }, []);

    useEffect(() => () => stopPolling(), [stopPolling]);

    const handleSearch = useCallback(async () => {
        if (!query.trim()) return;
        setError(null);
        setLoading(true);
        setResults([]);
        try {
            await startSearch(query.trim());
            startPolling();
        } catch (e) {
            setError(e.message);
            setLoading(false);
        }
    }, [query, startPolling]);

    const handleClear = useCallback(async () => {
        stopPolling();
        setLoading(false);
        setResults([]);
        setError(null);
        setQuery("");
        try {
            await clearResults();
            setStatus({ phase: "idle", running: false, urls_found: 0, results_count: 0, error: null, query: "" });
        } catch (e) {
            console.error("Temizleme hatası:", e);
        }
    }, [stopPolling]);

    return { query, setQuery, results, status, loading, error, handleSearch, handleClear };
}
