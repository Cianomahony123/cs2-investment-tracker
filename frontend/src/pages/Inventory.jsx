import { useState, useEffect, useMemo } from 'react'
import { api } from '../api/client'
import { useSteam } from '../context/SteamContext'
import SkinCard from '../components/SkinCard'
import PriceChart from '../components/PriceChart'
import './Inventory.css'

const SORT_OPTIONS = [
  { value: 'default',    label: 'Default' },
  { value: 'price-desc', label: 'Price: High → Low' },
  { value: 'price-asc',  label: 'Price: Low → High' },
  { value: 'trend-up',   label: 'Trending Up' },
  { value: 'trend-down', label: 'Trending Down' },
]

export default function Inventory() {
  const { steamId } = useSteam()
  const [manualId, setManualId] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [inventory, setInventory] = useState(null)
  const [selected, setSelected] = useState(null)
  const [history, setHistory] = useState(null)
  const [historyLoading, setHistoryLoading] = useState(false)
  const [sortBy, setSortBy] = useState('default')

  useEffect(() => {
    if (steamId && !inventory) loadInventory(steamId)
  }, [steamId])

  async function loadInventory(id, forceRefresh = false) {
    setLoading(true)
    setError(null)
    if (forceRefresh) setInventory(null)
    setSelected(null)
    try {
      const data = await api.getInventory(id, forceRefresh)
      setInventory(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleManualSubmit(e) {
    e.preventDefault()
    if (!manualId.trim()) return
    loadInventory(manualId.trim())
  }

  async function selectSkin(item) {
    setSelected(item)
    setHistory(null)
    setHistoryLoading(true)
    try {
      const h = await api.getPriceHistory(item.market_hash_name)
      setHistory(h)
    } catch {
      setHistory(null)
    } finally {
      setHistoryLoading(false)
    }
  }

  const sortedItems = useMemo(() => {
    if (!inventory) return []
    const items = [...inventory.items]
    switch (sortBy) {
      case 'price-desc': return items.sort((a, b) => (b.current_price ?? 0) - (a.current_price ?? 0))
      case 'price-asc':  return items.sort((a, b) => (a.current_price ?? 0) - (b.current_price ?? 0))
      case 'trend-up':   return items.sort((a, b) => (b.trend?.total_change_pct ?? -Infinity) - (a.trend?.total_change_pct ?? -Infinity))
      case 'trend-down': return items.sort((a, b) => (a.trend?.total_change_pct ?? Infinity) - (b.trend?.total_change_pct ?? Infinity))
      default: return items
    }
  }, [inventory, sortBy])

  return (
    <div>
      <div className="page-header">
        <h1>Inventory</h1>
        <p>
          {steamId
            ? 'Your CS2 inventory with live CSFloat and Steam Market prices.'
            : 'Log in with Steam or enter a Steam ID64 to load an inventory.'}
        </p>
      </div>

      {!steamId && (
        <form className="steam-form" onSubmit={handleManualSubmit}>
          <input
            className="input-field steam-input"
            type="text"
            placeholder="Steam ID64 (e.g. 76561198xxxxxxxxx)"
            value={manualId}
            onChange={e => setManualId(e.target.value)}
          />
          <button className="btn-primary" type="submit" disabled={loading}>
            {loading ? 'Loading…' : 'Load Inventory'}
          </button>
        </form>
      )}

      {steamId && inventory && (
        <button className="btn-secondary" style={{ marginBottom: 16 }} onClick={() => loadInventory(steamId, true)} disabled={loading}>
          Refresh from Steam
        </button>
      )}

      {error && <div className="error-msg">{error}</div>}
      {loading && <div className="loading">Fetching inventory and live prices…</div>}

      {inventory && (
        <>
          <div className="inventory-summary card">
            <div className="summary-stat">
              <span className="stat-label">Total Items</span>
              <span className="stat-value">{inventory.count}</span>
            </div>
            <div className="summary-stat">
              <span className="stat-label">Portfolio Value</span>
              <span className="stat-value accent">${inventory.total_value.toFixed(2)}</span>
            </div>
          </div>

          <div className="sort-bar">
            <span className="sort-label">Sort by</span>
            {SORT_OPTIONS.map(opt => (
              <button
                key={opt.value}
                className={`sort-btn${sortBy === opt.value ? ' active' : ''}`}
                onClick={() => setSortBy(opt.value)}
              >
                {opt.label}
              </button>
            ))}
          </div>

          {selected && (
            <div className="skin-detail card">
              <div className="detail-header">
                <img src={selected.icon_url} alt={selected.name} className="detail-img" />
                <div>
                  <div className="detail-name">{selected.name}</div>
                  <div className="detail-prices">
                    {selected.csfloat_price != null && (
                      <div className="detail-price-row">
                        <span className="source-dot source-cf" />
                        <span className="source-label">CSFloat</span>
                        <span className="detail-price-val">${selected.csfloat_price.toFixed(2)}</span>
                      </div>
                    )}
                    {selected.steam_price != null && (
                      <div className="detail-price-row">
                        <span className="source-dot source-steam" />
                        <span className="source-label">Steam</span>
                        <span className="detail-price-val steam">${selected.steam_price.toFixed(2)}</span>
                      </div>
                    )}
                  </div>
                  {selected.trend?.data_points >= 2 && (
                    <div className={selected.trend.total_change_pct >= 0 ? 'tag-up' : 'tag-down'} style={{ fontSize: 13, marginTop: 6 }}>
                      {selected.trend.total_change_pct >= 0 ? '+' : ''}{selected.trend.total_change_pct.toFixed(1)}% over 7 days
                    </div>
                  )}
                </div>
              </div>
              <div className="detail-chart">
                {historyLoading
                  ? <div className="loading">Loading chart…</div>
                  : <PriceChart data={history?.stored_history ?? []} height={160} />
                }
              </div>
              <button className="btn-secondary close-btn" onClick={() => setSelected(null)}>Close</button>
            </div>
          )}

          <div className="skin-grid">
            {sortedItems.map(item => (
              <SkinCard
                key={item.market_hash_name}
                item={item}
                onClick={() => selectSkin(item)}
              />
            ))}
          </div>
        </>
      )}
    </div>
  )
}
