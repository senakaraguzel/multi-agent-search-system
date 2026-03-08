const PHASE_LABELS = {
    idle: "Hazır",
    searching: "Arama yapılıyor...",
    extracting: "Detaylar çekiliyor...",
    done: "Tamamlandı",
    error: "Hata oluştu",
};

export default function StatusBar({ status }) {
    const { phase, query, urls_found, results_count, error } = status;

    return (
        <div className={`status-bar ${phase}`}>
            <div className={`status-dot ${phase}`} />
            <span className="status-text">
                {phase === "done" && query && (
                    <><strong>"{query}"</strong> için </>
                )}
                {phase === "extracting" && (
                    <><strong>{urls_found}</strong> URL bulundu, detaylar çekiliyor... </>
                )}
                {phase === "error" && error && (
                    <span style={{ color: "var(--error)" }}>{error.slice(0, 80)}</span>
                )}
                {PHASE_LABELS[phase] || phase}
            </span>

            <div className="status-stats">
                {results_count > 0 && (
                    <span className="stat-item">
                        Sonuç: <strong>{results_count}</strong>
                    </span>
                )}
                {urls_found > 0 && (
                    <span className="stat-item">
                        URL: <strong>{urls_found}</strong>
                    </span>
                )}
            </div>
        </div>
    );
}
