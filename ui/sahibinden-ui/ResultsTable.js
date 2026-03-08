import React from "react";

function ResultsTable({ data, headers }) {
    if (!data || data.length === 0) {
        return (
            <div className="empty-state">
                <div className="empty-icon">🏠</div>
                <p>Henüz sonuç yok. Yukarıdan bir arama yapın.</p>
            </div>
        );
    }

    const displayHeaders =
        headers && headers.length > 0
            ? headers
            : Object.keys(data[0]).map((k) => ({ key: k, label: k }));

    return (
        <>
            <div className="results-header">
                <div className="results-count">
                    <strong>{data.length}</strong> <span>ilan bulundu</span>
                </div>
            </div>

            <div className="table-wrapper">
                <table className="results-table">
                    <thead>
                        <tr>
                            {displayHeaders.map((h, i) => (
                                <th key={i}>{h.label}</th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {data.map((row, i) => (
                            <tr key={i}>
                                {displayHeaders.map((h, j) => {
                                    const value = row[h.key];
                                    const display =
                                        value !== null && value !== undefined
                                            ? String(value)
                                            : "—";

                                    if (h.key === "url" && value) {
                                        return (
                                            <td key={j}>
                                                <a
                                                    href={value}
                                                    target="_blank"
                                                    rel="noreferrer"
                                                    className="link-cell"
                                                    title={value}
                                                >
                                                    İlana Git ↗
                                                </a>
                                            </td>
                                        );
                                    }

                                    return (
                                        <td key={j} title={display}>
                                            {display}
                                        </td>
                                    );
                                })}
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </>
    );
}

export default ResultsTable;