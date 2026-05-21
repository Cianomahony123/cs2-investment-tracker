import { useState, useEffect } from 'react'
import { api } from '../api/client'
import { useSteam } from '../context/SteamContext'
import './Dashboard.css'

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
  const pct = item.total_change_pct
  const cls = pct > 0 ? 'tag-up' : pct < 0 ? 'tag-down' : 'tag-flat'
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
  const [manualId, setManualId] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [data, setData] = useState(null)

  useEffect(() => {
    if (steamId && !data) {
      load(steamId)
    }
  }, [steamId])

  async function load(id) {
    setLoading(true)
    setError(null)
    try {
      const inv = await api.getInventory(id)
      setData(inv)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleManualSubmit(e) {
    e.preventDefault()
    if (!manualId.trim()) return
    load(manualId.trim())
  }

  const gainers = data?.items
    .filter(i => i.trend?.data_points >= 2)
    .sort((a, b) => b.trend.total_change_pct - a.trend.total_change_pct)
    .slice(0, 5) ?? []

  const losers = data?.items
    .filter(i => i.trend?.data_points >= 2)
    .sort((a, b) => a.trend.total_change_pct - b.trend.total_change_pct)
    .slice(0, 5) ?? []

  return (
    <div>
      <div className="page-header">
        <h1>Dashboard</h1>
        <p>Portfolio overview with 7-day performance breakdown.</p>
      </div>

      {!steamId && (
        <form className="steam-form-dash" onSubmit={handleManualSubmit}>
          <input
            className="input-field"
            style={{ width: 280 }}
            type="text"
            placeholder="Steam ID64"
            value={manualId}
            onChange={e => setManualId(e.target.value)}
          />
          <button className="btn-primary" type="submit" disabled={loading}>
            {loading ? 'Loading…' : 'Load'}
          </button>
        </form>
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

      {!data && !loading && (
        <div className="empty-state card">
          <div className="empty-title">
            {steamId ? 'Loading your portfolio…' : 'Sign in with Steam to see your portfolio'}
          </div>
          <div className="empty-sub">
            {steamId
              ? 'Fetching inventory and live prices from CSFloat.'
              : 'Use the Sign in through Steam button in the top-right corner.'}
          </div>
        </div>
      )}
    </div>
  )
}
