import { useState, useEffect } from "react";

// Tüm alan tanımları — key→Türkçe/İngilizce etiket
const FIELD_DEFS = [
    { key: "name", label: "İşletme Adı", labelEn: "Name", always: true },
    { key: "rating", label: "Puan", labelEn: "Rating", always: true },
    { key: "reviews", label: "Değerlendirme", labelEn: "Reviews", score: 0 },
    { key: "address", label: "Adres", labelEn: "Address", score: 0 },
    { key: "phone", label: "Telefon", labelEn: "Phone", score: 0 },
    { key: "website", label: "Web Sitesi", labelEn: "Website", score: 0 },
    { key: "category", label: "Kategori", labelEn: "Category", score: 0 },
    { key: "source_url", label: "Maps URL", labelEn: "Maps URL", score: 0 },
];

// Sorgu ve doluluk oranına göre sütunları sıralar
function computeHeaders(query, results) {
    const q = (query || "").toLowerCase();
    const fields = FIELD_DEFS.map((f) => ({ ...f })); // kopya

    fields.forEach((f) => {
        if (f.always) { f.score = 100; return; }
        f.score = 0;

        // Doluluk oranı
        if (results.length > 0) {
            const filled = results.filter((r) => r[f.key] != null && r[f.key] !== "").length;
            f.score += (filled / results.length) * 40;
        }

        // Sorguya göre boost
        if (q.includes("web") && f.key === "website") f.score += 30;
        if (q.includes("puan") && f.key === "rating") f.score += 30;
        if (q.includes("telefon") && f.key === "phone") f.score += 30;
        if (q.includes("adres") && f.key === "address") f.score += 30;

        // Varsayılan öncelikler
        if (f.key === "address") f.score += 20;
        if (f.key === "phone") f.score += 15;
        if (f.key === "website") f.score += 15;
        if (f.key === "reviews") f.score += 10;
        if (f.key === "category") f.score += 8;
    });

    return fields.sort((a, b) => b.score - a.score);
}

export default function HeaderGenerator({ query, results, activeHeaders, onToggle }) {
    const [fields, setFields] = useState([]);

    useEffect(() => {
        setFields(computeHeaders(query, results));
    }, [query, results]);

    return (
        <div className="header-generator">
            <div className="hg-title">
                <span className="hg-icon">⚡</span>
                Header Generator — görüntülenecek sütunları seçin
            </div>
            <div className="hg-chips">
                {fields.map((f, i) => (
                    <button
                        key={f.key}
                        className={`hg-chip ${activeHeaders.includes(f.key) ? "active" : ""}`}
                        onClick={() => onToggle(f.key)}
                    >
                        <span className="chip-rank">{i + 1}</span>
                        {f.label}
                    </button>
                ))}
            </div>
        </div>
    );
}
