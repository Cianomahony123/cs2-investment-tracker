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
      <div className="rec-slope">{item.slope_pct > 0 ? '+' : ''}{item.slope_pct.toFixed(2)}%/day</div>
      <div className="rec-points">{item.data_points}d data</div>
    </div>
  )
}

const CLASSIFY_CLS = {
  'Strong Uptrend':   'ml-badge strong-up',
  'Uptrend':          'ml-badge up',
  'Sideways':         'ml-badge flat',
  'Downtrend':        'ml-badge down',
  'Strong Downtrend': 'ml-badge strong-down',
}

function MlRow({ item, rank }) {
  const cls = CLASSIFY_CLS[item.classification] ?? 'ml-badge flat'
  const changeCls = item.total_change_pct > 0 ? 'tag-up' : item.total_change_pct < 0 ? 'tag-down' : 'tag-flat'
  return (
    <div className="ml-row">
      <div className="rec-rank">#{rank}</div>
      <div className="ml-name">{item.market_hash_name}</div>
      <div className="ml-price">${item.current_price?.toFixed(2) ?? '—'}</div>
      <div className={changeCls} style={{ fontWeight: 700, fontSize: 13 }}>
        {item.total_change_pct > 0 ? '+' : ''}{item.total_change_pct.toFixed(1)}%
      </div>
      <div className="ml-score" title="Trend score = slope × R² + momentum boost">
        {item.trend_score > 0 ? '+' : ''}{item.trend_score.toFixed(2)}
      </div>
      <div className="ml-conf" title="R² — how well the linear model fits the price history">
        {(item.r_squared * 100).toFixed(0)}%
      </div>
      <div className="ml-days">{item.data_points}d</div>
      <div><span className={cls}>{item.classification}</span></div>
    </div>
  )
}

export default function Recommendations() {
  const [tab, setTab] = useState('weekly')
  const [loading, setLoading] = useState(false)
  const [seeding, setSeeding] = useState(false)
  const [error, setError] = useState(null)
  const [data, setData] = useState(null)
  const [mlData, setMlData] = useState(null)
  const [mlLoading, setMlLoading] = useState(false)
  const [seedResult, setSeedResult] = useState(null)

  useEffect(() => { loadWeekly() }, [])

  useEffect(() => {
    if (tab === 'ml' && !mlData) loadMl()
  }, [tab])

  async function loadWeekly() {
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

  async function loadMl() {
    setMlLoading(true)
    setError(null)
    try {
      const d = await api.getMlTrends(30)
      setMlData(d)
    } catch (err) {
      setError(err.message)
    } finally {
      setMlLoading(false)
    }
  }

  async function seed() {
    setSeeding(true)
    setSeedResult(null)
    try {
      const r = await api.seedWatchlist()
      setSeedResult(r)
      await loadWeekly()
      setMlData(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setSeeding(false)
    }
  }

  return (
    <div>
      <div className="page-header">
        <h1>Recommendations</h1>
        <p>Price trend analysis powered by daily snapshots and linear regression.</p>
      </div>

      <div className="rec-controls">
        <button className="btn-secondary" onClick={tab === 'weekly' ? loadWeekly : loadMl} disabled={loading || mlLoading}>
          {loading || mlLoading ? 'Refreshing…' : 'Refresh'}
        </button>
        <button className="btn-primary" onClick={seed} disabled={seeding}>
          {seeding ? 'Seeding…' : 'Seed Watchlist & Snapshot'}
        </button>
        <span className="rec-hint">Seed adds popular skins and records today's prices. Run daily to build history.</span>
      </div>

      {seedResult && (
        <div className="seed-result card">
          Added <strong>{seedResult.added_to_watchlist}</strong> new skins ({seedResult.total_seeded} total tracked).
        </div>
      )}

      {error && <div className="error-msg">{error}</div>}

      <div className="rec-tabs">
        <button className={`rec-tab${tab === 'weekly' ? ' active' : ''}`} onClick={() => setTab('weekly')}>
          Weekly Picks
        </button>
        <button className={`rec-tab${tab === 'ml' ? ' active' : ''}`} onClick={() => setTab('ml')}>
          ML Analysis
        </button>
      </div>

      {tab === 'weekly' && (
        <>
          {loading && <div className="loading">Loading…</div>}
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
                    Click <strong>Seed Watchlist &amp; Snapshot</strong> above, then come back tomorrow so there
                    are at least 3 data points to calculate a trend.
                  </div>
                </div>
              ) : (
                <div className="rec-table card">
                  <div className="rec-table-header">
                    <span>#</span><span>Skin</span><span>Price</span>
                    <span>7d Change</span><span>Slope</span><span>Data</span>
                  </div>
                  {data.recommendations.map((item, i) => (
                    <RecommendationRow key={item.market_hash_name} item={item} rank={i + 1} />
                  ))}
                </div>
              )}
            </>
          )}
        </>
      )}

      {tab === 'ml' && (
        <>
          {mlLoading && <div className="loading">Running ML analysis…</div>}
          {mlData && (
            <>
              <div className="rec-meta-bar">
                <span>{mlData.total_analyzed} skins analyzed</span>
                <span className="tag-flat">Generated {new Date(mlData.generated_at).toLocaleString()}</span>
              </div>
              <div className="ml-legend">
                <span className="ml-legend-item"><strong>Trend Score</strong> = slope × R² + momentum — higher is a stronger, more confident uptrend</span>
                <span className="ml-legend-item"><strong>Confidence (R²)</strong> — how consistently the price follows the trend line (100% = perfect)</span>
              </div>

              {mlData.trends.length === 0 ? (
                <div className="card empty-rec">
                  <div style={{ fontWeight: 600, marginBottom: 8 }}>No historical data yet</div>
                  <div style={{ color: 'var(--text-dim)', fontSize: 13, lineHeight: 1.6 }}>
                    Seed the watchlist and come back after collecting several days of price snapshots.
                  </div>
                </div>
              ) : (
                <div className="rec-table card">
                  <div className="ml-table-header">
                    <span>#</span><span>Skin</span><span>Price</span>
                    <span>Change</span><span>Score</span><span>R²</span>
                    <span>Days</span><span>Classification</span>
                  </div>
                  {mlData.trends.map((item, i) => (
                    <MlRow key={item.market_hash_name} item={item} rank={i + 1} />
                  ))}
                </div>
              )}
            </>
          )}
        </>
      )}

      <div className="rec-disclaimer">
        Trend scores use linear regression (slope × R²) plus momentum over all available price history.
        Past performance does not indicate future results.
      </div>
    </div>
  )
}
