const BASE = import.meta.env.VITE_API_URL ?? '/api'

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, options)
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Request failed' }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

export const api = {
  getInventory: (steamId, forceRefresh = false) =>
    request(`/inventory/${steamId}${forceRefresh ? '?refresh=true' : ''}`),

  getPriceHistory: (name) =>
    request(`/prices/${encodeURIComponent(name)}/history`),

  forceSnapshot: (name) =>
    request(`/prices/${encodeURIComponent(name)}/snapshot`, { method: 'POST' }),

  getRecommendations: (limit = 10) =>
    request(`/recommendations/?limit=${limit}`),

  seedWatchlist: () =>
    request('/recommendations/seed-watchlist', { method: 'POST' }),
}
