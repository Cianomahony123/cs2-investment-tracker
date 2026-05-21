import './SkinCard.css'

function TrendBadge({ trend }) {
  if (!trend || trend.data_points < 2) return <span className="trend-badge flat">No data</span>
  const pct = trend.total_change_pct
  const cls = pct > 0 ? 'up' : pct < 0 ? 'down' : 'flat'
  const sign = pct > 0 ? '+' : ''
  return <span className={`trend-badge ${cls}`}>{sign}{pct.toFixed(1)}% (7d)</span>
}

export default function SkinCard({ item, onClick }) {
  const { name, icon_url, exterior, rarity, current_price, total_value, quantity, trend } = item

  return (
    <div className="skin-card" onClick={onClick} role={onClick ? 'button' : undefined}>
      <div className="skin-img-wrap">
        <img src={icon_url} alt={name} className="skin-img" loading="lazy" />
      </div>
      <div className="skin-info">
        <div className="skin-name">{name}</div>
        <div className="skin-meta">
          {exterior && <span className="meta-tag">{exterior}</span>}
          {rarity && <span className="meta-tag rarity">{rarity}</span>}
        </div>
        <div className="skin-pricing">
          <div className="price-row">
            <span className="price-label">Price</span>
            <span className="price-value">
              {current_price != null ? `$${current_price.toFixed(2)}` : '—'}
            </span>
          </div>
          {quantity > 1 && (
            <div className="price-row">
              <span className="price-label">Total ({quantity}x)</span>
              <span className="price-value">${total_value.toFixed(2)}</span>
            </div>
          )}
        </div>
        <TrendBadge trend={trend} />
      </div>
    </div>
  )
}
