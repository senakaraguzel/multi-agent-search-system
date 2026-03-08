import { useState } from 'react'
import { EvidenceDrawer } from './EvidenceDrawer'
import { DynamicTable } from './DynamicTable'

/**
 * result.json'daki verileri tek bir dinamik tablo yapısında render eder.
 */
export function SectionRenderer({ data: resultData, sources, validationNote }) {
    const result = resultData?.final_structured_result || {}
    // Tum handler'larin kullandigi olasi veri anahtarlarini kontrol et
    const items = result.data ||
        result.profiles ||
        result.results ||
        result.businesses ||
        result.articles ||
        result.listings ||
        []
    const summary = result.summary_stats || result.title_breakdown || result.overall_synthesis

    if (!items.length && !summary) {
        return (
            <div className="section">
                <div className="section-header">Sonuçlar</div>
                <div className="section-body" style={{ color: '#64748b', fontSize: 14 }}>
                    ℹ️ Sonuç bulunamadı (No data available)
                </div>
            </div>
        )
    }

    return (
        <div className="section">
            <div className="section-header">
                Arama Sonuçları Listesi
                {items.length > 0 && <span className="item-count">{items.length} kayıt</span>}
            </div>
            <div className="section-body">
                {/* Ozet bilgileri (varsa) */}
                {summary && (
                    <div className="stats-summary" style={{ marginBottom: 16 }}>
                        {typeof summary === 'string' ? (
                            <p>{summary}</p>
                        ) : summary.note ? (
                            <p style={{ fontSize: 13, color: '#94a3b8' }}>{summary.note}</p>
                        ) : (
                            <div className="breakdown-tags">
                                {Object.entries(summary).map(([k, v]) => (
                                    <div key={k} className="b-tag">
                                        <strong>{k}:</strong> {v}
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                )}

                {/* Dinamik Tablo Render */}
                {items.length > 0 && <DynamicTable items={items} />}

                {/* Kaynaklar ve Notlar */}
                <div style={{ marginTop: 20 }}>
                    <EvidenceDrawer sources={sources} validationNote={validationNote} />
                </div>
            </div>
        </div>
    )
}

