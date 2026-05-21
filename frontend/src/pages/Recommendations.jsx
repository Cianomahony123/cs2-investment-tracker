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
      <div className="ml-score">{item.trend_score > 0 ? '+' : ''}{item.trend_score.toFixed(2)}</div>
      <div className="ml-conf">{(item.r_squared * 100).toFixed(0)}%</div>
      <div className="ml-days">{item.data_points}d</div>
      <div><span className={cls}>{item.classification}</span></div>
    </div>
  )
}

export default function Recommendations() {
  const [tab, setTab] = useState('weekly')
  const [loading, setLoading] = useState(false)
  const [seeding, setSeeding] = useState(false)
  const [backfilling, setBackfilling] = useState(false)
  const [error, setError] = useState(null)
  const [data, setData] = useState(null)
  const [mlData, setMlData] = useState(null)
  const [mlLoading, setMlLoading] = useState(false)
  const [seedResult, setSeedResult] = useState(null)
  const [backfillResult, setBackfillResult] = useState(null)

  useEffect(() => { loadWeekly() }, [])

  useEffect(() => {
    if (tab === 'ml' && !mlData) loadMl()
  }, [tab])

  async function loadWeekly() {
    setLoading(true); setError(null)
    try { setData(await api.getRecommendations(15)) }
    catch (err) { setError(err.message) }
    finally { setLoading(false) }
  }

  async function loadMl() {
    setMlLoading(true); setError(null)
    try { setMlData(await api.getMlTrends(30)) }
    catch (err) { setError(err.message) }
    finally { setMlLoading(false) }
  }

  async function seed() {
    setSeeding(true); setSeedResult(null)
    try {
      const r = await api.seedWatchlist()
      setSeedResult(r)
      await loadWeekly()
      setMlData(null)
    } catch (err) { setError(err.message) }
    finally { setSeeding(false) }
  }

  async function backfill() {
    setBackfilling(true); setBackfillResult(null)
    try {
      const r = await api.backfillHistory()
      setBackfillResult(r)
      setMlData(null)
      if (tab === 'ml') loadMl()
    } catch (err) { setError(err.message) }
    finally { setBackfilling(false) }
  }

  return (
    <div>
      <div className="page-header">
        <h1>Recommendations</h1>
        <p>AI-powered skin picks for the CS2 investment community.</p>
      </div>

      <div className="rec-controls">
        <button className="btn-secondary" onClick={tab === 'weekly' ? loadWeekly : loadMl} disabled={loading || mlLoading}>
          {loading || mlLoading ? 'Refreshing…' : 'Refresh'}
        </button>
        <button className="btn-primary" onClick={seed} disabled={seeding}>
          {seeding ? 'Seeding…' : 'Seed Watchlist & Snapshot'}
        </button>
        <button className="btn-secondary" onClick={backfill} disabled={backfilling}>
          {backfilling ? 'Backfilling history…' : 'Backfill History'}
        </button>
        <span className="rec-hint">Seed adds popular skins + today's prices. Backfill mines sold-listing dates for instant multi-day history.</span>
      </div>

      {seedResult && (
        <div className="seed-result card">
          Added <strong>{seedResult.added_to_watchlist}</strong> new skins ({seedResult.total_seeded} total tracked).
        </div>
      )}
      {backfillResult && (
        <div className="seed-result card">
          Backfilled <strong>{backfillResult.filled}</strong> historical snapshots across {backfillResult.skins_processed} skins.
        </div>
      )}

      {error && <div className="error-msg">{error}</div>}

      <div className="rec-tabs">
        <button className={`rec-tab${tab === 'weekly' ? ' active' : ''}`} onClick={() => setTab('weekly')}>Weekly Picks</button>
        <button className={`rec-tab${tab === 'ml' ? ' active' : ''}`} onClick={() => setTab('ml')}>ML Analysis</button>
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
                    Click <strong>Seed Watchlist &amp; Snapshot</strong> then <strong>Backfill History</strong> to populate data immediately.
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
          {mlLoading && <div className="loading">Running analysis…</div>}
          {mlData && (
            <>
              <div className="rec-meta-bar">
                <span>{mlData.total_analyzed} skins analyzed</span>
                <span className="tag-flat">Generated {new Date(mlData.generated_at).toLocaleString()}</span>
              </div>

              <div className="ml-legend">
                <p className="ml-intro">
                  Our investment algorithm helps hobby players make smarter decisions in the CS2 skin economy.
                  It analyses price history using linear regression to spot skins with genuine upward momentum —
                  filtering out noise so you see only the cleanest trends.
                </p>
                <div className="ml-legend-items">
                  <span className="ml-legend-item"><strong>Trend Score</strong> — overall signal strength: a high score means consistent upward movement, not just a one-day spike</span>
                  <span className="ml-legend-item"><strong>Confidence</strong> — how reliably the skin follows its trend (higher = more predictable, lower = more volatile)</span>
                </div>
              </div>

              {mlData.trends.length === 0 ? (
                <div className="card empty-rec">
                  <div style={{ fontWeight: 600, marginBottom: 8 }}>No historical data yet</div>
                  <div style={{ color: 'var(--text-dim)', fontSize: 13, lineHeight: 1.6 }}>
                    Use <strong>Backfill History</strong> to pull real sold-listing dates from CSFloat and populate multi-day history immediately.
                  </div>
                </div>
              ) : (
                <div className="rec-table card">
                  <div className="ml-table-header">
                    <span>#</span><span>Skin</span><span>Price</span>
                    <span>Change</span><span>Score</span><span>Confidence</span>
                    <span>Days</span><span>Signal</span>
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
        Algorithm output is for informational purposes only. Past price trends do not guarantee future results.
        Always do your own research before investing.
      </div>
    </div>
  )
}
