import { useState, useEffect, useRef } from 'react'
import './index.css'
import { QueryHeader } from './components/QueryHeader'
import { SearchBar } from './components/SearchBar'
import { SectionRenderer } from './components/SectionRenderer'

const POLL_MS = 4000

function App() {
  const [state, setState] = useState({
    data: null, loading: false, searching: false, resuming: false, error: '', hasSearched: false
  })
  const pollingRef = useRef(null)

  const fetchResult = () => {
    fetch('/api/result')
      .then(r => r.json())
      .then(json => setState(s => {
        if (s.searching || s.resuming) return s
        return { ...s, data: json, loading: false }
      }))
      .catch(() => setState(s => ({ ...s, loading: false })))
  }

  useEffect(() => {
    setState(s => ({ ...s, loading: true }))
    fetchResult()
    pollingRef.current = setInterval(fetchResult, POLL_MS)
    return () => clearInterval(pollingRef.current)
  }, [])

  const handleSearch = async (query) => {
    setState(s => ({ ...s, searching: true, error: '', data: null, hasSearched: true }))
    try {
      const res = await fetch('/api/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
      })
      const json = await res.json()
      if (json.stale_result) {
        const errMsg = json.error
          ? `Pipeline hatası: ${json.error}`
          : 'Arama tamamlanamadı. Chrome tarayıcısı açık ve CDP aktif olmalı (port 9222).'
        setState(s => ({ ...s, data: null, searching: false, error: errMsg }))
        return
      }
      if (json.error && !json.raw_result?.original_query) {
        setState(s => ({ ...s, error: json.error, searching: false }))
        return
      }
      setState(s => ({ ...s, data: json, searching: false }))
    } catch (e) {
      setState(s => ({ ...s, searching: false, error: `Bağlantı hatası: ${e.message}` }))
    }
  }

  // Sadece scrape + filter adımlarını çalıştır (Agent 1-2-3 atlanır)
  const handleResume = async () => {
    setState(s => ({ ...s, resuming: true, error: '', hasSearched: true }))
    try {
      const res = await fetch('/api/resume', { method: 'POST' })
      const json = await res.json()
      if (json.error) {
        setState(s => ({ ...s, resuming: false, error: `Hata: ${json.error}` }))
        return
      }
      setState(s => ({ ...s, data: json, resuming: false }))
    } catch (e) {
      setState(s => ({ ...s, resuming: false, error: `Bağlantı hatası: ${e.message}` }))
    }
  }

  const { data, loading, searching, resuming, error, hasSearched } = state
  const result = data?.raw_result || {}
  const summary = data?.llm_summary || ''
  const updated = data?.last_updated || ''
  const queryType = data?.query_type || 'generic'
  const sources = result.sources_used || []
  const note = result.validation_notes || ''
  const hasResult = hasSearched && Boolean(result.original_query)

  return (
    <div className="app-shell">
      {/* ── Top bar ── */}
      <div className="page-header">
        <h1>Genarion Searcher</h1>
        <div className="refresh-dot" title="Canlı" />
      </div>

      {/* ── Arama Kutusu + Devam Et ── */}
      <div className="search-row">
        <SearchBar onSearch={handleSearch} searching={searching || resuming} />
        <button
          className="resume-btn"
          onClick={handleResume}
          disabled={searching || resuming}
          title="Agent 1-2-3 atlanarak sadece Scrape + Filter çalışır (URL'ler zaten toplandıysa kullan)"
        >
          {resuming ? '⏳ Devam ediyor…' : '▶ Devam Et'}
        </button>
      </div>

      {/* ── Hata mesajı ── */}
      {error && (
        <div className="error-banner">⚠️ {error}</div>
      )}

      {/* ── Yükleniyor ── */}
      {loading && !hasResult && (
        <div className="center-msg">
          <div className="spinner" />
          Yükleniyor…
        </div>
      )}

      {/* ── İşlem çalışıyor ── */}
      {(searching || resuming) && (
        <div className="center-msg">
          <div className="spinner" />
          {resuming ? 'Scrape & Filter çalışıyor…' : 'Pipeline çalışıyor, lütfen bekleyin…'}
        </div>
      )}

      {/* ── Sonuçlar ── */}
      {!searching && !resuming && hasResult && (
        <>
          <QueryHeader
            data={result}
            lastUpdated={updated}
            queryType={queryType}
          />
          {summary && (
            <div className="summary-card">
              <span className="summary-icon">🤖</span>
              <p className="summary-text">{summary}</p>
            </div>
          )}
          <SectionRenderer
            data={result}
            sources={sources}
            validationNote={note}
          />
        </>
      )}

      {/* ── Başlangıç ekranı ── */}
      {!loading && !searching && !resuming && !hasResult && (
        <div className="center-msg">
          👆 Yukarıya bir sorgu girin ve <strong>Ara</strong> butonuna basın.<br />
          <small style={{ opacity: 0.6 }}>URL'ler zaten toplandıysa <strong>▶ Devam Et</strong> ile başa dönmeden devam edin.</small>
        </div>
      )}
    </div>
  )
}

export default App
