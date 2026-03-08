const API_BASE = "http://localhost:8000";

export async function fetchResults() {
  const res = await fetch(`${API_BASE}/api/results`);
  if (!res.ok) throw new Error("Sonuçlar alınamadı");
  return res.json();
}

export async function fetchStatus() {
  const res = await fetch(`${API_BASE}/api/status`);
  if (!res.ok) throw new Error("Durum alınamadı");
  return res.json();
}

export async function startSearch(query, maxScrolls = 30) {
  const res = await fetch(`${API_BASE}/api/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, max_scrolls: maxScrolls }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Arama başlatılamadı");
  }
  return res.json();
}

export async function clearResults() {
  const res = await fetch(`${API_BASE}/api/results`, { method: "DELETE" });
  if (!res.ok) throw new Error("Temizleme başarısız");
  return res.json();
}
