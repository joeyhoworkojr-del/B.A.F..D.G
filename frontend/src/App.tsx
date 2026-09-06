import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Suspense, lazy } from 'react'
import { TopBar } from './components/TopBar'
import { BottomNav } from './components/BottomNav'
import { Dashboard } from './pages/Dashboard'

// Route-level code splitting: only the Game Center ships in the initial
// bundle; every other page loads on demand.
const lazyPage = <T extends string>(load: () => Promise<Record<T, React.ComponentType>>, name: T) =>
  lazy(() => load().then(m => ({ default: m[name] })))

const GameDetail = lazyPage(() => import('./pages/GameDetail'), 'GameDetail')
const BestBets = lazyPage(() => import('./pages/BestBets'), 'BestBets')
const Parlay = lazyPage(() => import('./pages/Parlay'), 'Parlay')
const TrackRecord = lazyPage(() => import('./pages/TrackRecord'), 'TrackRecord')
const About = lazyPage(() => import('./pages/About'), 'About')

function PageFallback() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-6 space-y-4">
      <div className="skeleton h-8 w-56 rounded" />
      <div className="skeleton h-64 w-full rounded-2xl" />
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen text-zinc-100">
        <TopBar />
        <main className="pb-20">
          <Suspense fallback={<PageFallback />}>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/game/:league/:eventId" element={<GameDetail />} />
              <Route path="/best-bets" element={<BestBets />} />
              <Route path="/parlay" element={<Parlay />} />
              <Route path="/track" element={<TrackRecord />} />
              <Route path="/about" element={<About />} />
            </Routes>
          </Suspense>
        </main>
        <BottomNav />
      </div>
    </BrowserRouter>
  )
}
