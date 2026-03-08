import { useState } from 'react'

/** Expandable sources + validation_notes */
export function EvidenceDrawer({ sources = [], validationNote = '' }) {
    const [open, setOpen] = useState(false)
    if (!sources.length && !validationNote) return null

    return (
        <>
            <button className="evidence-btn" onClick={() => setOpen(o => !o)}>
                <span>{open ? '▲' : '▼'}</span>
                {open ? 'Kaynakları Gizle' : `Kaynakları Göster (${sources.length})`}
            </button>
            {open && (
                <div className="evidence-drawer">
                    {sources.map((s, i) => (
                        <div key={i} className="evidence-source">
                            <a href={s} target="_blank" rel="noreferrer" style={{ color: 'inherit' }}>
                                🔗 {s.length > 80 ? s.slice(0, 80) + '…' : s}
                            </a>
                        </div>
                    ))}
                    {validationNote && (
                        <div className="evidence-note">📝 {validationNote}</div>
                    )}
                </div>
            )}
        </>
    )
}
