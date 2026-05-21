import { useState, useEffect } from 'react'
import { api } from '../api/client'
import './Recommendations.css'

function RecommendationRow({ item, rank }) {
  const pct = item.total_change_pct
  const cls = pct > 0 ? 'tag-up' : pct < 0 ? 'tag-down' : 'tag-flat'
  const sign = pct > 0 ? '+' : ''

  return (
    <div className="rec-row">
      <div className="rec-rank">#{rank}</div>
      <div className="rec-name">{item.market_hash_name}</div>
      <div className="rec-meta">
        <span className="rec-price">${item.current_price?.toFixed(2) ?? '—'}</span>
        <span className="rec-start">from ${item.start_price?.toFixed(2) ?? '—'}</span>
      </div>
      <div className={`rec-pct ${cls}`}>{sign}{pct.toFixed(1)}%</div>
      <div className="rec-slope" title="% gain per day (regression slope)">
        {item.slope_pct > 0 ? '+' : ''}{item.slope_pct.toFixed(2)}%/day
      </div>
      <div className="rec-points">{item.data_points}d data</div>
    </div>
  )
}

export default function Recommendations() {
  const [loading, setLoading] = useState(false)
  const [seeding, setSeeding] = useState(false)
  const [error, setError] = useState(null)
  const [data, setData] = useState(null)
  const [seedResult, setSeedResult] = useState(null)

  useEffect(() => { load() }, [])

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const d = await api.getRecommendations(15)
      setData(d)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function seed() {
    setSeeding(true)
    setSeedResult(null)
    try {
      const r = await api.seedWatchlist()
      setSeedResult(r)
      await load()
    } catch (err) {
      setError(err.message)
    } finally {
      setSeeding(false)
    }
  }

  return (
    <div>
      <div className="page-header">
        <h1>Weekly Picks</h1>
        <p>CS2 skins with the strongest upward 7-day price trend on CSFloat.</p>
      </div>

      <div className="rec-controls">
        <button className="btn-secondary" onClick={load} disabled={loading}>
          {loading ? 'Refreshing…' : 'Refresh'}
        </button>
        <button className="btn-primary" onClick={seed} disabled={seeding}>
          {seeding ? 'Seeding…' : 'Seed Watchlist & Snapshot'}
        </button>
        <span className="rec-hint">
          Seed adds 50 popular skins and takes today's price. Run daily to build trend data.
        </span>
      </div>

      {seedResult && (
        <div className="seed-result card">
          Added <strong>{seedResult.added_to_watchlist}</strong> new skins to watchlist
          ({seedResult.total_seeded} total tracked).
        </div>
      )}

      {error && <div className="error-msg">{error}</div>}

      {data && (
        <>
          <div className="rec-meta-bar">
            <span>{data.recommendations.length} trending skins</span>
            <span className="tag-flat">Updated {new Date(data.generated_at).toLocaleString()}</span>
          </div>

          {data.recommendations.length === 0 ? (
            <div className="card empty-rec">
              <div style={{ fontWeight: 600, marginBottom: 8 }}>No trend data yet</div>
              <div style={{ color: 'var(--text-dim)', fontSize: 13, lineHeight: 1.6 }}>
                Click <strong>Seed Watchlist &amp; Snapshot</strong> above, then come back tomorrow
                (or run it again after some time) so there are at least 3 data points to calculate a trend.
              </div>
            </div>
          ) : (
            <div className="rec-table card">
              <div className="rec-table-header">
                <span>#</span>
                <span>Skin</span>
                <span>Price</span>
                <span>7d Change</span>
                <span>Slope</span>
                <span>Data</span>
              </div>
              {data.recommendations.map((item, i) => (
                <RecommendationRow key={item.market_hash_name} item={item} rank={i + 1} />
              ))}
            </div>
          )}

          <div className="rec-disclaimer">
            Price trend is calculated via linear regression over stored daily snapshots.
            Past performance does not indicate future results. Always do your own research.
          </div>
        </>
      )}
    </div>
  )
}
