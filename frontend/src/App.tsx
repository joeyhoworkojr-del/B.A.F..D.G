import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { NavBar } from './components/NavBar'
import { Dashboard } from './pages/Dashboard'
import { Predict } from './pages/Predict'
import { Today } from './pages/Today'
import { NFL } from './pages/NFL'
import { CFL } from './pages/CFL'
import { MLB } from './pages/MLB'
import { BestBets } from './pages/BestBets'
import { Rankings } from './pages/Rankings'
import { History } from './pages/History'
import { About } from './pages/About'

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen text-zinc-100">
        <NavBar />
        <main>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/soccer" element={<Predict />} />
            <Route path="/today" element={<Today />} />
            <Route path="/nfl" element={<NFL />} />
            <Route path="/cfl" element={<CFL />} />
            <Route path="/mlb" element={<MLB />} />
            <Route path="/best-bets" element={<BestBets />} />
            <Route path="/rankings" element={<Rankings />} />
            <Route path="/history" element={<History />} />
            <Route path="/about" element={<About />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
