import React from 'react'

/** 
 * Verilen objelerdeki property'leri cikararak dinamik tablo olusturur. 
 * 'url', 'profile_url', 'source_url' gibi alanlari "İlana Git" seklinde link yapar.
 */
export function DynamicTable({ items }) {
    if (!items || items.length === 0) return null

    // Butun ogelerden (item) tum anahtarlari (keys) topla
    const columnsSet = new Set()
    items.forEach(item => {
        Object.keys(item).forEach(k => {
            if (k === 'details' && typeof item[k] === 'object' && item[k] !== null) {
                // Details icindeki anahtarlari ana kolon yap
                Object.keys(item[k]).forEach(subK => columnsSet.add(subK))
            } else {
                columnsSet.add(k)
            }
        })
    })

    // 'details' kolonunu kendisini gosterme (icindekileri cikardik)
    const columns = Array.from(columnsSet).filter(c => c !== 'details')

    const formatHeader = (key) => {
        return key.replace(/_/g, ' ').toUpperCase()
    }

    const isUrl = (key, val) => {
        const k = key.toLowerCase()
        return (k.includes('url') || k.includes('link') || k === 'source') && typeof val === 'string' && val.startsWith('http')
    }

    return (
        <div className="dynamic-table-container">
            <table className="dynamic-table">
                <thead>
                    <tr>
                        {columns.map((col, i) => (
                            <th key={i}>{formatHeader(col)}</th>
                        ))}
                    </tr>
                </thead>
                <tbody>
                    {items.map((item, rowIndex) => (
                        <tr key={rowIndex}>
                            {columns.map((col, colIndex) => {
                                // Deger ana itemda mı yoksa details icinde mi?
                                let val = item[col]
                                if (val === undefined && item.details && typeof item.details === 'object') {
                                    val = item.details[col]
                                }

                                if (isUrl(col, val)) {
                                    return (
                                        <td key={colIndex}>
                                            <a href={val} target="_blank" rel="noreferrer" className="table-link" title={val}>
                                                🔗 Kaynağa Git
                                            </a>
                                        </td>
                                    )
                                }

                                // Eger deger hala bir objeyse (beklenmedik durum) stringlestir
                                const displayVal = (typeof val === 'object' && val !== null)
                                    ? JSON.stringify(val)
                                    : (val !== undefined && val !== null ? String(val) : '—')

                                return (
                                    <td key={colIndex}>
                                        {displayVal}
                                    </td>
                                )
                            })}
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    )
}
