import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { SteamProvider } from './context/SteamContext'
import Navbar from './components/Navbar'
import Dashboard from './pages/Dashboard'
import Inventory from './pages/Inventory'
import Recommendations from './pages/Recommendations'

function RootRedirect() {
  const location = useLocation()
  return <Navigate to={`/inventory${location.search}`} replace />
}

export default function App() {
  return (
    <SteamProvider>
      <div className="app">
        <Navbar />
        <main className="main-content">
          <Routes>
            <Route path="/" element={<RootRedirect />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/inventory" element={<Inventory />} />
            <Route path="/recommendations" element={<Recommendations />} />
          </Routes>
        </main>
      </div>
    </SteamProvider>
  )
}
