import type { AdjustmentOut, WeatherInfoOut } from '../types'

interface Props {
  conditions: AdjustmentOut[]
  weather?: WeatherInfoOut | null
  /** Headline probability before conditions (0–1) */
  baseProb?: number
  /** Headline probability after conditions (0–1) */
  currentProb?: number
  baseLabel?: string
}

function sourceIcon(source: string): string {
  return source === 'weather' ? '🌦' : '🩹'
}

export function ConditionsPanel({ conditions, weather, baseProb, currentProb, baseLabel }: Props) {
  const hasShift =
    baseProb !== undefined && currentProb !== undefined && Math.abs(currentProb - baseProb) >= 0.005

  if (conditions.length === 0 && !weather) return null

  return (
    <div className="rounded-lg border border-signal-blue/30 bg-signal-blue/5 px-3 py-2 space-y-2">
      <div className="flex items-center justify-between">
        <p className="text-[10px] font-display uppercase tracking-widest text-signal-blue">
          Live conditions {conditions.length > 0 ? `(${conditions.length} active)` : ''}
        </p>
        {weather && (
          <span className="text-xs font-mono text-zinc-400">
            {weather.is_indoor
              ? '🏟️ Indoor'
              : `${weather.condition} · ${weather.temperature_c.toFixed(0)}°C · 💨 ${weather.wind_speed_kmh.toFixed(0)} km/h`}
          </span>
        )}
      </div>

      {conditions.length === 0 && weather && (
        <p className="text-xs text-zinc-500 font-body">
          Weather checked — conditions are neutral, no model adjustment needed.
        </p>
      )}

      {conditions.map((c, i) => (
        <div key={i} className="flex items-start gap-2">
          <span className="text-sm leading-5">{sourceIcon(c.source)}</span>
          <div className="min-w-0">
            <p className="text-xs font-display font-medium text-zinc-200">{c.label}</p>
            <p className="text-[11px] text-zinc-500 font-body">{c.detail}</p>
          </div>
        </div>
      ))}

      {hasShift && (
        <p className="text-xs font-mono border-t border-signal-blue/20 pt-2 text-zinc-300">
          {baseLabel ?? 'Win probability'}:{' '}
          <span className="text-zinc-500">{Math.round(baseProb! * 100)}%</span>
          <span className="text-zinc-600"> → </span>
          <span className={currentProb! > baseProb! ? 'text-signal-green' : 'text-signal-red'}>
            {Math.round(currentProb! * 100)}%
          </span>{' '}
          <span className="text-zinc-600">after live conditions</span>
        </p>
      )}
    </div>
  )
}
