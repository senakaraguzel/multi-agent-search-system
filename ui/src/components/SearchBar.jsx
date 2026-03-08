import { useState } from 'react'

/** Arama formu — kullanıcı sorgu girer, /api/search'e POST atar */
export function SearchBar({ onSearch, searching }) {
    const [query, setQuery] = useState('')

    const submit = (e) => {
        e.preventDefault()
        if (query.trim() && !searching) onSearch(query.trim())
    }

    return (
        <form className="search-form" onSubmit={submit}>
            <div className="search-input-wrap">
                <span className="search-icon">🔍</span>
                <input
                    type="text"
                    className="search-input"
                    placeholder="Bir sorgu girin… (ör. Hamburg'daki imbissler, Galatasaray golleri)"
                    value={query}
                    onChange={e => setQuery(e.target.value)}
                    disabled={searching}
                />
                <button
                    type="submit"
                    className={`search-btn ${searching ? 'searching' : ''}`}
                    disabled={searching || !query.trim()}
                >
                    {searching ? (
                        <><span className="btn-spinner" /> Aranıyor…</>
                    ) : 'Ara'}
                </button>
            </div>
            {searching && (
                <p className="search-hint">
                    Pipeline çalışıyor — bu birkaç dakika sürebilir ☕
                </p>
            )}
        </form>
    )
}
