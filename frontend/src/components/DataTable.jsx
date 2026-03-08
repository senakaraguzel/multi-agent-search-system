import { useState } from "react";
import ResultCard from "./ResultCard";

function formatDomain(url) {
    try { return new URL(url).hostname.replace("www.", ""); } catch { return url; }
}

const COLUMN_DEFS = {
    "name": {
        label: "İŞLETME ADI",
        render: (v) => <span className="cell-name" title={v}>{v || <span className="null-badge">—</span>}</span>,
    },
    "rating": {
        label: "PUAN",
        render: (v) => v ? <span className="rating-badge">⭐ {v}</span> : <span className="null-badge">—</span>,
    },
    "reviews": {
        label: "DEĞERLENDİRME",
        render: (v) => v ? <span style={{ fontSize: 12, color: "var(--text-muted)" }}>({v})</span> : <span className="null-badge">—</span>,
    },
    "address": {
        label: "ADRES",
        render: (v) => (
            <span title={v} style={{ display: "block", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: 220 }}>
                {v || <span className="null-badge">—</span>}
            </span>
        ),
    },
    "phone": {
        label: "TELEFON",
        render: (v) => <span className="cell-phone">{v || <span className="null-badge">—</span>}</span>,
    },
    "website": {
        label: "WEB SİTESİ",
        render: (v) => v
            ? <a className="cell-link" href={v} target="_blank" rel="noreferrer" onClick={(e) => e.stopPropagation()}>{formatDomain(v)}</a>
            : <span className="null-badge">—</span>,
    },
    "category": {
        label: "KATEGORİ",
        render: (v) => <span>{v || <span className="null-badge">—</span>}</span>,
    },
    "source_url": {
        label: "URL",
        render: (v) => v
            ? <a className="cell-link" href={v} target="_blank" rel="noreferrer" onClick={(e) => e.stopPropagation()}>Haritaya Git ↗</a>
            : <span className="null-badge">—</span>,
    },
};

export default function DataTable({ results, activeHeaders }) {
    const [selected, setSelected] = useState(null);

    const visibleHeaders = activeHeaders.filter((h) => COLUMN_DEFS[h]);

    if (results.length === 0) {
        return (
            <div className="empty-state">
                <div className="empty-icon">🔍</div>
                <h3>Henüz sonuç yok</h3>
                <p>Yukarıdaki arama kutusuna bir sorgu girin ve aramayı başlatın.</p>
            </div>
        );
    }

    return (
        <div className="data-table-container">
            <div className="table-result-count">
                <strong>{results.length}</strong> işletme bulundu
            </div>

            <div className="table-wrapper">
                <table className="data-table">
                    <thead>
                        <tr>
                            {visibleHeaders.map((h) => (
                                <th key={h}>{COLUMN_DEFS[h].label}</th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {results.map((row, i) => (
                            <tr
                                key={i}
                                className={selected === i ? "selected" : ""}
                                onClick={() => setSelected(selected === i ? null : i)}
                            >
                                {visibleHeaders.map((h) => (
                                    <td key={h}>{COLUMN_DEFS[h]?.render(row[h])}</td>
                                ))}
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {selected !== null && results[selected] && (
                <ResultCard result={results[selected]} onClose={() => setSelected(null)} />
            )}
        </div>
    );
}
