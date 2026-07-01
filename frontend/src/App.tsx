import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { NavBar } from './components/NavBar'
import { Predict } from './pages/Predict'
import { NFL } from './pages/NFL'
import { Rankings } from './pages/Rankings'
import { History } from './pages/History'
import { About } from './pages/About'

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-terminal-bg text-zinc-100">
        <NavBar />
        <main>
          <Routes>
            <Route path="/" element={<Predict />} />
            <Route path="/nfl" element={<NFL />} />
            <Route path="/rankings" element={<Rankings />} />
            <Route path="/history" element={<History />} />
            <Route path="/about" element={<About />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
