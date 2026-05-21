import { useState, useEffect } from 'react'
import { api } from '../api/client'
import { useSteam } from '../context/SteamContext'
import './Dashboard.css'

const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api'

function SteamIcon() {
  return (
    <svg viewBox="0 0 24 24" width="20" height="20" fill="#fff" xmlns="http://www.w3.org/2000/svg" style={{ flexShrink: 0 }}>
      <path d="M11.979 0C5.678 0 .511 4.86.022 11.037l6.432 2.658c.545-.371 1.203-.59 1.912-.59.063 0 .125.004.188.006l2.861-4.142V8.91c0-2.495 2.028-4.524 4.524-4.524 2.494 0 4.524 2.031 4.524 4.527s-2.03 4.525-4.524 4.525h-.105l-4.076 2.911c0 .052.004.105.004.159 0 1.875-1.515 3.396-3.39 3.396-1.635 0-3.016-1.173-3.331-2.727L.436 15.27C1.862 20.307 6.486 24 11.979 24c6.627 0 11.999-5.373 11.999-12S18.605 0 11.979 0zM7.54 18.21l-1.473-.61c.262.543.714.999 1.314 1.25 1.297.539 2.793-.076 3.332-1.375.263-.63.264-1.319.005-1.949s-.75-1.121-1.377-1.383c-.624-.26-1.29-.249-1.878-.03l1.523.63c.956.4 1.409 1.492 1.009 2.447-.397.957-1.497 1.406-2.455 1.02zm11.415-9.303c0-1.662-1.353-3.015-3.015-3.015-1.665 0-3.015 1.353-3.015 3.015 0 1.665 1.35 3.015 3.015 3.015 1.663 0 3.015-1.35 3.015-3.015zm-5.273-.005c0-1.252 1.013-2.266 2.265-2.266 1.249 0 2.266 1.014 2.266 2.266 0 1.251-1.017 2.265-2.266 2.265-1.252 0-2.265-1.014-2.265-2.265z"/>
    </svg>
  )
}

function StatCard({ label, value, sub, accent }) {
  return (
    <div className="stat-card card">
      <div className="stat-card-label">{label}</div>
      <div className={`stat-card-value${accent ? ' accent' : ''}`}>{value}</div>
      {sub && <div className="stat-card-sub">{sub}</div>}
    </div>
  )
}

function TrendRow({ item }) {
  const pct  = item.trend?.total_change_pct ?? 0
  const cls  = pct > 0 ? 'tag-up' : pct < 0 ? 'tag-down' : 'tag-flat'
  const sign = pct > 0 ? '+' : ''
  return (
    <div className="trend-row">
      <span className="trend-name">{item.market_hash_name}</span>
      <span className="trend-price">${item.current_price?.toFixed(2) ?? '—'}</span>
      <span className={cls}>{sign}{pct.toFixed(1)}%</span>
    </div>
  )
}

export default function Dashboard() {
  const { steamId } = useSteam()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [data, setData] = useState(null)

  useEffect(() => {
    if (!steamId) { setData(null); return }
    if (!data) load(steamId)
  }, [steamId])

  async function load(id) {
    setLoading(true)
    setError(null)
    try {
      setData(await api.getInventory(id))
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const gainers = data?.items
    .filter(i => i.trend?.data_points >= 2)
    .sort((a, b) => (b.trend?.total_change_pct ?? 0) - (a.trend?.total_change_pct ?? 0))
    .slice(0, 5) ?? []

  const losers = data?.items
    .filter(i => i.trend?.data_points >= 2)
    .sort((a, b) => (a.trend?.total_change_pct ?? 0) - (b.trend?.total_change_pct ?? 0))
    .slice(0, 5) ?? []

  return (
    <div>
      <div className="page-header">
        <h1>Dashboard</h1>
        <p>Portfolio overview with 7-day performance breakdown.</p>
      </div>

      {!steamId && (
        <div className="dash-signin card">
          <div className="empty-title">Sign in to view your portfolio</div>
          <div className="empty-sub">
            See your CS2 inventory value, 7-day price movers, and top gainers — all in one place.
          </div>
          <a href={`${API}/auth/steam`} className="dash-steam-btn">
            <SteamIcon />
            Sign in with Steam
          </a>
        </div>
      )}

      {error && <div className="error-msg">{error}</div>}
      {loading && <div className="loading">Fetching portfolio…</div>}

      {data && (
        <>
          <div className="stats-row">
            <StatCard label="Portfolio Value" value={`$${data.total_value.toFixed(2)}`} accent />
            <StatCard label="Total Skins" value={data.count} />
            <StatCard
              label="Trending Up"
              value={data.items.filter(i => (i.trend?.total_change_pct ?? 0) > 0).length}
              sub="skins gaining this week"
            />
            <StatCard
              label="Trending Down"
              value={data.items.filter(i => (i.trend?.total_change_pct ?? 0) < 0).length}
              sub="skins losing this week"
            />
          </div>

          <div className="movers-grid">
            <div className="card">
              <div className="movers-title tag-up">Top Gainers (7d)</div>
              {gainers.length === 0
                ? <p className="no-data">Not enough price history yet</p>
                : gainers.map(i => <TrendRow key={i.market_hash_name} item={i} />)
              }
            </div>
            <div className="card">
              <div className="movers-title tag-down">Biggest Losers (7d)</div>
              {losers.length === 0
                ? <p className="no-data">Not enough price history yet</p>
                : losers.map(i => <TrendRow key={i.market_hash_name} item={i} />)
              }
            </div>
          </div>
        </>
      )}

      {steamId && !data && !loading && !error && (
        <div className="empty-state card">
          <div className="empty-title">Loading your portfolio…</div>
          <div className="empty-sub">Fetching inventory and live prices.</div>
        </div>
      )}
    </div>
  )
}
