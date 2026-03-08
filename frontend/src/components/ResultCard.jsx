const FIELDS = [
    { key: "name", label: "İşletme Adı" },
    { key: "rating", label: "Puan" },
    { key: "reviews", label: "Değerlendirme" },
    { key: "phone", label: "Telefon" },
    { key: "website", label: "Web Sitesi", isLink: true },
    { key: "address", label: "Adres", full: true },
    { key: "category", label: "Kategori" },
    { key: "source_url", label: "Google Maps URL", isLink: true, full: true },
];

export default function ResultCard({ result, onClose }) {
    return (
        <div className="detail-overlay" onClick={onClose}>
            <div className="detail-panel" onClick={(e) => e.stopPropagation()}>
                <div className="detail-header">
                    <div className="detail-title">
                        <h2>{result["name"] || "Bilinmeyen"}</h2>
                        {result["source_url"] && (
                            <a
                                className="source-link"
                                href={result["source_url"]}
                                target="_blank"
                                rel="noreferrer"
                            >
                                🗺 Google Maps'te Görüntüle ↗
                            </a>
                        )}
                    </div>
                    <button className="detail-close" onClick={onClose}>✕</button>
                </div>

                <div className="detail-grid">
                    {FIELDS.map(({ key, label, isLink, full }) => (
                        <div key={key} className={`detail-field ${full ? "full-width" : ""}`}>
                            <div className="field-label">{label}</div>
                            <div className="field-value">
                                {result[key] ? (
                                    isLink ? (
                                        <a href={result[key]} target="_blank" rel="noreferrer">
                                            {result[key].length > 60
                                                ? result[key].slice(0, 60) + "…"
                                                : result[key]}
                                        </a>
                                    ) : (
                                        result[key]
                                    )
                                ) : (
                                    <span style={{ color: "var(--text-muted)", fontStyle: "italic" }}>
                                        Bilgi yok
                                    </span>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}
