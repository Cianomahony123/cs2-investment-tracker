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
    if (!steamId) { setInventory(null); setSelected(null); return }
    if (!inventory) loadInventory(steamId)
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
      {steamId ? (
        <div className="page-header">
          <h1>Inventory</h1>
          <p>Your CS2 inventory with live CSFloat and Steam Market prices.</p>
        </div>
      ) : (
        <div className="hero">
          <div className="hero-tag">CS2 Investment Tracker</div>
          <h1 className="hero-title">
            Know what your skins are worth.<br />
            Know when to move.
          </h1>
          <p className="hero-sub">
            Real-time pricing from CSFloat and Steam Market. AI-driven trend detection across hundreds of skins.
            Your personal edge in the CS2 economy — sign in and let the data do the talking.
          </p>
          <div className="hero-features">
            <span className="hero-feat">📈 Live dual-market prices</span>
            <span className="hero-feat">🔍 7-day momentum tracking</span>
            <span className="hero-feat">🤖 Market Algorithm picks</span>
            <span className="hero-feat">💰 Full portfolio valuation</span>
          </div>
          <a href={`${import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api'}/auth/steam`} className="hero-cta steam-login-btn">
            <svg viewBox="0 0 24 24" className="steam-svg" xmlns="http://www.w3.org/2000/svg">
              <path d="M11.979 0C5.678 0 .511 4.86.022 11.037l6.432 2.658c.545-.371 1.203-.59 1.912-.59.063 0 .125.004.188.006l2.861-4.142V8.91c0-2.495 2.028-4.524 4.524-4.524 2.494 0 4.524 2.031 4.524 4.527s-2.03 4.525-4.524 4.525h-.105l-4.076 2.911c0 .052.004.105.004.159 0 1.875-1.515 3.396-3.39 3.396-1.635 0-3.016-1.173-3.331-2.727L.436 15.27C1.862 20.307 6.486 24 11.979 24c6.627 0 11.999-5.373 11.999-12S18.605 0 11.979 0zM7.54 18.21l-1.473-.61c.262.543.714.999 1.314 1.25 1.297.539 2.793-.076 3.332-1.375.263-.63.264-1.319.005-1.949s-.75-1.121-1.377-1.383c-.624-.26-1.29-.249-1.878-.03l1.523.63c.956.4 1.409 1.492 1.009 2.447-.397.957-1.497 1.406-2.455 1.02zm11.415-9.303c0-1.662-1.353-3.015-3.015-3.015-1.665 0-3.015 1.353-3.015 3.015 0 1.665 1.35 3.015 3.015 3.015 1.663 0 3.015-1.35 3.015-3.015zm-5.273-.005c0-1.252 1.013-2.266 2.265-2.266 1.249 0 2.266 1.014 2.266 2.266 0 1.251-1.017 2.265-2.266 2.265-1.252 0-2.265-1.014-2.265-2.265z"/>
            </svg>
            Sign in with Steam to get started
          </a>
        </div>
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


