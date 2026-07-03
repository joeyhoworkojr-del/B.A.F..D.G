import { useState, useEffect, useCallback } from 'react'

interface WeatherData {
  temperature_c: number
  temperature_f: number
  precipitation_prob: number
  wind_speed_kmh: number
  condition: string
  is_indoor: boolean
  source: string
}

interface Props {
  venue: string
  refreshIntervalMs?: number   // default 1 hour
}

const BASE = (import.meta.env.VITE_API_BASE ?? 'http://localhost:8000').replace(/\/+$/, '')

function wmoEmoji(condition: string): string {
  const c = condition.toLowerCase()
  if (c.includes('thunder')) return '⛈️'
  if (c.includes('snow')) return '❄️'
  if (c.includes('heavy rain') || c.includes('heavy shower')) return '🌧️'
  if (c.includes('rain') || c.includes('shower') || c.includes('drizzle')) return '🌦️'
  if (c.includes('fog')) return '🌫️'
  if (c.includes('overcast')) return '☁️'
  if (c.includes('partly') || c.includes('cloudy')) return '⛅'
  return '☀️'
}

export function WeatherWidget({ venue, refreshIntervalMs = 3_600_000 }: Props) {
  const [data, setData] = useState<WeatherData | null>(null)
  const [loading, setLoading] = useState(false)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)

  const fetchWeather = useCallback(async () => {
    setLoading(true)
    try {
      // Encode venue name for URL
      const encoded = encodeURIComponent(venue)
      const resp = await fetch(`${BASE}/api/v1/weather/${encoded}`)
      if (resp.ok) {
        const json = await resp.json()
        setData(json as WeatherData)
        setLastUpdated(new Date())
      }
    } catch {
      // Silently fail — weather is supplementary info
    } finally {
      setLoading(false)
    }
  }, [venue])

  useEffect(() => {
    if (venue) {
      fetchWeather()
      const interval = setInterval(fetchWeather, refreshIntervalMs)
      return () => clearInterval(interval)
    }
    return undefined
  }, [venue, fetchWeather, refreshIntervalMs])

  if (!venue || (!data && !loading)) return null

  if (loading && !data) {
    return (
      <div className="flex items-center gap-2 text-xs text-zinc-600 font-body animate-pulse">
        <span>🌡️</span> Loading weather…
      </div>
    )
  }

  if (!data) return null

  const emoji = data.is_indoor ? '🏟️' : wmoEmoji(data.condition)
  const rainAlert = data.precipitation_prob >= 60 && !data.is_indoor

  return (
    <div className={`rounded-lg border px-3 py-2 flex flex-wrap items-center gap-4 text-xs font-body
      ${rainAlert
        ? 'border-signal-blue/40 bg-signal-blue/5'
        : 'border-terminal-border bg-terminal-surface'
      }`}
    >
      <div className="flex items-center gap-1.5">
        <span className="text-base">{emoji}</span>
        <span className="text-zinc-300">
          {data.is_indoor ? 'Indoor venue' : data.condition}
        </span>
      </div>

      {!data.is_indoor && (
        <>
          <span className="font-mono text-signal-amber">
            {data.temperature_c.toFixed(1)}°C / {data.temperature_f.toFixed(0)}°F
          </span>
          <span className="text-zinc-500">
            💨 {data.wind_speed_kmh.toFixed(0)} km/h
          </span>
          <span className={data.precipitation_prob >= 60 ? 'text-signal-blue font-medium' : 'text-zinc-500'}>
            🌧 {data.precipitation_prob}% rain
          </span>
        </>
      )}

      {rainAlert && (
        <span className="text-signal-blue font-display font-semibold">
          Rain likely — adds variance, not goals
        </span>
      )}

      <span className="ml-auto text-zinc-600">
        {lastUpdated ? `Updated ${lastUpdated.toLocaleTimeString()}` : ''} · Open-Meteo
      </span>

      <button
        onClick={fetchWeather}
        disabled={loading}
        className="text-zinc-600 hover:text-zinc-300 transition-colors"
        title="Refresh weather"
      >
        🔄
      </button>
    </div>
  )
}
