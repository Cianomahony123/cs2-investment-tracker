import { NavLink } from 'react-router-dom'
import { useSteam } from '../context/SteamContext'
import './Navbar.css'

export default function Navbar() {
  const { steamId, logout } = useSteam()

  return (
    <nav className="navbar">
      <div className="navbar-brand">
        <span className="brand-icon">CS2</span>
        <span className="brand-text">Investment Tracker</span>
      </div>
      <div className="navbar-links">
        <NavLink to="/dashboard" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
          Dashboard
        </NavLink>
        <NavLink to="/inventory" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
          Inventory
        </NavLink>
        <NavLink to="/recommendations" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
          Weekly Picks
        </NavLink>
      </div>
      <div className="navbar-auth">
        {steamId ? (
          <div className="auth-logged-in">
            <span className="auth-id" title={steamId}>
              {steamId.slice(-6)}
            </span>
            <button className="btn-logout" onClick={logout}>Logout</button>
          </div>
        ) : (
          <a href={`${import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api'}/auth/steam`} className="steam-login-btn">
            <img
              src="https://steamcommunity-a.akamaihd.net/public/images/signinthroughsteam/sits_02.png"
              alt="Sign in through Steam"
              className="steam-login-img"
            />
          </a>
        )}
      </div>
    </nav>
  )
}
