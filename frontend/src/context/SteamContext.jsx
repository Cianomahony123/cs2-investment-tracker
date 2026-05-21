import { createContext, useContext, useState, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'

const SteamContext = createContext(null)

export function SteamProvider({ children }) {
  const [steamId, setSteamId] = useState(() => localStorage.getItem('steam_id') ?? null)
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()

  useEffect(() => {
    const id = searchParams.get('steam_id')
    if (id) {
      localStorage.setItem('steam_id', id)
      setSteamId(id)
      // Clean the query param from the URL
      searchParams.delete('steam_id')
      setSearchParams(searchParams, { replace: true })
      navigate('/inventory', { replace: true })
    }
  }, [])

  function logout() {
    localStorage.removeItem('steam_id')
    setSteamId(null)
  }

  return (
    <SteamContext.Provider value={{ steamId, logout }}>
      {children}
    </SteamContext.Provider>
  )
}

export function useSteam() {
  return useContext(SteamContext)
}
