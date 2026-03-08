/** Google Maps / Lokal firma kartı */
export function ListingCard({ item }) {
    const {
        company_name, address, phone,
        rating, reviews_count, category, source_url,
        // LinkedIn / genel
        name, title, company, location,
        // Genel fallback
        title: fallbackTitle, details, source_note
    } = item

    // Lokal firma mı?
    if (company_name) {
        return (
            <div className="listing-card">
                {category && <div className="lc-category">{category}</div>}
                <div className="lc-name">{company_name}</div>
                {address && <div className="lc-row"><span>📍</span>{address}</div>}
                {phone && <div className="lc-row"><span>📞</span>{phone}</div>}
                {rating && (
                    <div className="lc-rating">
                        ⭐ {rating}
                        {reviews_count && <small>({reviews_count.toLocaleString()} yorum)</small>}
                    </div>
                )}
                {source_url && (
                    <a href={source_url} target="_blank" rel="noreferrer"
                        style={{ fontSize: 11, color: '#6366f1', marginTop: 8, display: 'block' }}>
                        Haritada Gör →
                    </a>
                )}
            </div>
        )
    }

    // LinkedIn profili
    if (name) {
        return (
            <div className="listing-card">
                <div className="lc-name">{name}</div>
                {title && <div className="lc-row"><span>💼</span>{title}</div>}
                {company && <div className="lc-row"><span>🏢</span>{company}</div>}
                {location && <div className="lc-row"><span>📍</span>{location}</div>}
            </div>
        )
    }

    // LLM üretimi genel kayıt (stats/listing)
    return (
        <div className="generic-item">
            {(fallbackTitle) && <div className="gi-title">{fallbackTitle}</div>}
            {details && (
                <div className="gi-detail">
                    {Object.entries(details).map(([k, v]) => (
                        <span key={k} style={{ marginRight: 14 }}>
                            <strong style={{ color: '#94a3b8' }}>{k}:</strong>{' '}
                            <strong>{v ?? '—'}</strong>
                        </span>
                    ))}
                </div>
            )}
            {source_note && <div className="gi-meta">📌 {source_note}</div>}
        </div>
    )
}
