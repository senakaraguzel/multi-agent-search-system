const API_BASE = "http://127.0.0.1:8000";

/**
 * Sahibinden.com'da arama yapar.
 * @returns {Promise<{data: Array, headers: Array}>}
 *   headers: [{key, label}, ...]
 *   data:    [{title, price, ...}, ...]
 */
export async function searchListings(query) {

    const response = await fetch(`${API_BASE}/search`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ query }),
    });

    if (!response.ok) {
        throw new Error(`Sunucu hatası: ${response.status} ${response.statusText}`);
    }

    const data = await response.json();

    if (data.status === "error") {
        throw new Error(data.message || "Bilinmeyen hata");
    }

    return {
        data: data.data,
        headers: data.headers,
    };
}
