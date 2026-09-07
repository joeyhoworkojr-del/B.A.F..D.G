import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Suspense, lazy } from 'react'
import { TopBar } from './components/layout/TopBar'
import { BottomNav } from './components/layout/BottomNav'
import { MobileMoreLinks } from './components/layout/MobileMoreLinks'
import { Footer } from './components/layout/Footer'
import { Dashboard } from './pages/Dashboard'

// Route-level code splitting: only the games board ships in the initial
// bundle; every other page loads on demand.
const lazyPage = <T extends string>(load: () => Promise<Record<T, React.ComponentType>>, name: T) =>
  lazy(() => load().then(m => ({ default: m[name] })))

const GameDetail = lazyPage(() => import('./pages/GameDetail'), 'GameDetail')
const BestBets = lazyPage(() => import('./pages/BestBets'), 'BestBets')
const Parlay = lazyPage(() => import('./pages/Parlay'), 'Parlay')
const TrackRecord = lazyPage(() => import('./pages/TrackRecord'), 'TrackRecord')
const About = lazyPage(() => import('./pages/About'), 'About')
const Account = lazyPage(() => import('./pages/Account'), 'Account')
const News = lazyPage(() => import('./pages/News'), 'News')
const Live = lazyPage(() => import('./pages/Live'), 'Live')
const Props = lazyPage(() => import('./pages/Props'), 'Props')
const Faq = lazyPage(() => import('./pages/Faq'), 'Faq')

function PageFallback() {
  return (
    <div className="mx-auto w-full max-w-app px-4 py-6 space-y-4">
      <div className="skeleton h-8 w-56 rounded" />
      <div className="skeleton h-64 w-full rounded-2xl" />
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex min-h-screen flex-col text-zinc-100">
        <TopBar />
        <MobileMoreLinks />
        <main className="flex-1 pb-24 md:pb-10">
          <Suspense fallback={<PageFallback />}>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/game/:league/:eventId" element={<GameDetail />} />
              <Route path="/live" element={<Live />} />
              <Route path="/props" element={<Props />} />
              <Route path="/best-bets" element={<BestBets />} />
              <Route path="/news" element={<News />} />
              <Route path="/results" element={<TrackRecord />} />
              {/* Older links to /track still work. */}
              <Route path="/track" element={<Navigate to="/results" replace />} />
              <Route path="/parlay" element={<Parlay />} />
              <Route path="/faq" element={<Faq />} />
              <Route path="/about" element={<About />} />
              <Route path="/account" element={<Account />} />
            </Routes>
          </Suspense>
        </main>
        <Footer />
        <BottomNav />
      </div>
    </BrowserRouter>
  )
}
