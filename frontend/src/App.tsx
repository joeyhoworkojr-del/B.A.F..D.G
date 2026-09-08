import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Suspense, lazy } from 'react'
import { TopBar } from './components/layout/TopBar'
import { BottomNav } from './components/layout/BottomNav'
import { MobileMoreLinks } from './components/layout/MobileMoreLinks'
import { Footer } from './components/layout/Footer'
import { SessionProvider } from './session/SessionProvider'
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
const NotFound = lazyPage(() => import('./pages/NotFound'), 'NotFound')
const Login = lazyPage(() => import('./pages/Login'), 'Login')
const Register = lazyPage(() => import('./pages/Register'), 'Register')
const Onboarding = lazyPage(() => import('./pages/Onboarding'), 'Onboarding')
const MyEdge = lazyPage(() => import('./pages/MyEdge'), 'MyEdge')
const Analyst = lazyPage(() => import('./pages/Analyst'), 'Analyst')
const Leaderboard = lazyPage(() => import('./pages/Leaderboard'), 'Leaderboard')
const Staff = lazyPage(() => import('./pages/Staff'), 'Staff')

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
      <SessionProvider>
      <div className="flex min-h-screen flex-col text-zinc-100">
        <TopBar />
        <MobileMoreLinks />
        <main className="flex-1 pb-24 lg:pb-10">
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
              <Route path="/login" element={<Login />} />
              <Route path="/register" element={<Register />} />
              <Route path="/onboarding" element={<Onboarding />} />
              <Route path="/my-edge" element={<MyEdge />} />
              <Route path="/leaderboard" element={<Leaderboard />} />
              <Route path="/staff" element={<Staff />} />
              {/* Analyst handles are the clean public URL: /@username */}
              <Route path="/:username" element={<Analyst />} />
              {/* The SPA fallback serves index.html for any path, so without
                  this an unknown URL rendered an empty page. */}
              <Route path="*" element={<NotFound />} />
            </Routes>
          </Suspense>
        </main>
        <Footer />
        <BottomNav />
      </div>
      </SessionProvider>
    </BrowserRouter>
  )
}
