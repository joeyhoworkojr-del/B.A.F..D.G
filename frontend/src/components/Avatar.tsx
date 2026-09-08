import type { PublicProfile, PrivateProfile } from '../types'

type AnyProfile = Pick<PublicProfile & PrivateProfile, 'username' | 'display_name' | 'avatar_url'>

/** Up to two letters from the name someone actually goes by. */
export function initials(user: Pick<AnyProfile, 'username' | 'display_name'>): string {
  const name = (user.display_name || user.username || '').trim()
  const words = name.split(/\s+/).filter(Boolean)
  if (words.length >= 2) return (words[0][0] + words[1][0]).toUpperCase()
  return name.slice(0, 2).toUpperCase() || '??'
}

/**
 * A person, everywhere they appear.
 *
 * One component so a profile photo shows up consistently in the nav, on
 * leaderboards, beside picks and in chat. Without a photo it falls back to
 * clean initials rather than a generic silhouette — a placeholder that says
 * who it is beats one that says nothing.
 */
export function Avatar({
  user, size = 32, className = '',
}: { user: AnyProfile; size?: number; className?: string }) {
  const px = `${size}px`
  const label = user.display_name || user.username

  if (user.avatar_url) {
    return (
      <img
        src={user.avatar_url}
        alt=""
        width={size}
        height={size}
        loading="lazy"
        // Decorative: every use site already names the person in adjacent text,
        // so alt text here would be read out twice.
        className={`shrink-0 rounded-full border border-terminal-border object-cover ${className}`}
        style={{ width: px, height: px }}
      />
    )
  }

  return (
    <span
      aria-hidden="true"
      title={label}
      className={`grid shrink-0 place-items-center rounded-full bg-brand-soft font-bold uppercase text-brand ${className}`}
      style={{ width: px, height: px, fontSize: `${Math.round(size * 0.38)}px` }}
    >
      {initials(user)}
    </span>
  )
}
