/** Sorgu tipine göre dinamik başlık bilgisi */
export const QUERY_TYPE_META = {
  local: { icon: '🗺️', label: 'Lokal Firma Araması', color: '#22c55e' },
  categoric: { icon: '📰', label: 'Kategorik Arama', color: '#f59e0b' },
  platform: { icon: '🏪', label: 'Platform Araması', color: '#8b5cf6' },
  specific: { icon: '📊', label: 'Spesifik Bilgi Araması', color: '#6366f1' },
  generic: { icon: '🔍', label: 'Arama Sonuçları', color: '#94a3b8' },
}

/** Sorgu başlığı — confidence bar yok */
export function QueryHeader({ data, lastUpdated, queryType }) {
  const { original_query } = data
  const meta = QUERY_TYPE_META[queryType] || QUERY_TYPE_META.generic

  return (
    <div className="query-card">
      {/* Dinamik tip etiketi */}
      <div className="query-type-badge" style={{ color: meta.color }}>
        <span>{meta.icon}</span>
        {meta.label}
      </div>
      {/* Sorgu metni */}
      <div className="query-text">{original_query || '—'}</div>
      {lastUpdated && (
        <div className="last-updated" style={{ marginTop: 6 }}>
          Son güncelleme: {lastUpdated}
        </div>
      )}
    </div>
  )
}
