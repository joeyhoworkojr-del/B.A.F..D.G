import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Suspense, lazy } from 'react'
import { NavBar } from './components/NavBar'
import { TickerTape } from './components/TickerTape'
import { Dashboard } from './pages/Dashboard'

// Route-level code splitting: only the dashboard ships in the initial bundle;
// every other page (and its heavy chart deps) loads on demand.
const lazyPage = <T extends string>(load: () => Promise<Record<T, React.ComponentType>>, name: T) =>
  lazy(() => load().then(m => ({ default: m[name] })))

const Predict = lazyPage(() => import('./pages/Predict'), 'Predict')
const Today = lazyPage(() => import('./pages/Today'), 'Today')
const NFL = lazyPage(() => import('./pages/NFL'), 'NFL')
const CFL = lazyPage(() => import('./pages/CFL'), 'CFL')
const MLB = lazyPage(() => import('./pages/MLB'), 'MLB')
const BestBets = lazyPage(() => import('./pages/BestBets'), 'BestBets')
const Rankings = lazyPage(() => import('./pages/Rankings'), 'Rankings')
const History = lazyPage(() => import('./pages/History'), 'History')
const TrackRecord = lazyPage(() => import('./pages/TrackRecord'), 'TrackRecord')
const About = lazyPage(() => import('./pages/About'), 'About')

function PageFallback() {
  return (
    <div className="mx-auto max-w-5xl px-4 py-10 space-y-4">
      <div className="skeleton h-8 w-56 rounded" />
      <div className="skeleton h-64 w-full rounded-xl" />
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen text-zinc-100">
        <NavBar />
        <TickerTape />
        <main>
          <Suspense fallback={<PageFallback />}>
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
              <Route path="/track" element={<TrackRecord />} />
              <Route path="/about" element={<About />} />
            </Routes>
          </Suspense>
        </main>
      </div>
    </BrowserRouter>
  )
}
