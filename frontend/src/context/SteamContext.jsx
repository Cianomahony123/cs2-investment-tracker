import { createContext, useContext, useState, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'

const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api'
const AuthContext = createContext(null)

function decodeJwt(token) {
  try {
    const payload = token.split('.')[1]
    return JSON.parse(atob(payload.replace(/-/g, '+').replace(/_/g, '/')))
  } catch {
    return null
  }
}

export function SteamProvider({ children }) {
  const [steamId, setSteamId] = useState(() => localStorage.getItem('steam_id') ?? null)
  const [steamProfile, setSteamProfile] = useState(() => {
    const name   = localStorage.getItem('steam_name')
    const avatar = localStorage.getItem('steam_avatar')
    return name ? { name, avatar: avatar || '' } : null
  })
  const [googleUser, setGoogleUser] = useState(() => {
    const raw = localStorage.getItem('google_token')
    return raw ? decodeJwt(raw) : null
  })
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()

  useEffect(() => {
    const steamParam  = searchParams.get('steam_id')
    const googleParam = searchParams.get('google_token')

    if (steamParam) {
      localStorage.setItem('steam_id', steamParam)
      setSteamId(steamParam)
      searchParams.delete('steam_id')
      setSearchParams(searchParams, { replace: true })
      navigate('/inventory', { replace: true })
      fetch(`${API}/auth/steam/profile/${steamParam}`)
        .then(r => r.json())
        .then(p => {
          if (p.name) {
            localStorage.setItem('steam_name', p.name)
            localStorage.setItem('steam_avatar', p.avatar || '')
            setSteamProfile({ name: p.name, avatar: p.avatar || '' })
          }
        })
        .catch(() => {})
    } else if (googleParam) {
      const user = decodeJwt(googleParam)
      if (user) {
        localStorage.setItem('google_token', googleParam)
        setGoogleUser(user)
      }
      searchParams.delete('google_token')
      setSearchParams(searchParams, { replace: true })
      navigate('/recommendations', { replace: true })
    }
  }, [])

  function logout() {
    localStorage.removeItem('steam_id')
    localStorage.removeItem('steam_name')
    localStorage.removeItem('steam_avatar')
    localStorage.removeItem('google_token')
    setSteamId(null)
    setSteamProfile(null)
    setGoogleUser(null)
  }

  return (
    <AuthContext.Provider value={{ steamId, steamProfile, googleUser, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useSteam() {
  return useContext(AuthContext)
}
