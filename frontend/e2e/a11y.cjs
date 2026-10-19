/**
 * The colour-contrast audit, as a string evaluated in the page.
 *
 * It exists because an audit of the whole app found seven distinct colour
 * pairs below WCAG AA — emerald-600 text on white at 3.77:1, white on
 * emerald-600 at the same, red-600 on red-100 at 3.95:1, and a "faint"
 * grey being used for text at 2.54:1. None of that was visible by reading
 * the code: each one was a token that looked right in isolation and failed
 * against the surface it ended up on. Running it on every page at every
 * width is the only way that stays fixed.
 *
 * It walks every element that renders its own text, finds the nearest opaque
 * background behind it, and applies the AA threshold for that text's size and
 * weight: 3:1 for large text (24px, or 18.66px bold), 4.5:1 otherwise.
 */
const CONTRAST_AUDIT = `(() => {
  const srgb = c => { c /= 255; return c <= 0.03928 ? c/12.92 : Math.pow((c+0.055)/1.055, 2.4) }
  const lum = p => 0.2126*srgb(p[0]) + 0.7152*srgb(p[1]) + 0.0722*srgb(p[2])
  const parse = s => {
    const m = String(s).match(/rgba?\\(([^)]+)\\)/)
    if (!m) return null
    const p = m[1].split(',').map(Number)
    return { rgb: p.slice(0, 3), a: p.length > 3 ? p[3] : 1 }
  }
  const ratio = (a, b) => {
    const l1 = lum(a), l2 = lum(b), hi = Math.max(l1, l2), lo = Math.min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)
  }
  const bad = []
  for (const el of document.querySelectorAll('*')) {
    // Only elements with a text node of their own: a wrapper inherits the
    // colour of whatever is inside it and would be counted twice.
    const own = [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())
    if (!own) continue
    const cs = getComputedStyle(el)
    if (cs.visibility === 'hidden' || cs.display === 'none' || Number(cs.opacity) < 0.5) continue
    const box = el.getBoundingClientRect()
    if (!box.width || !box.height) continue
    const fg = parse(cs.color)
    if (!fg || fg.a < 0.5) continue
    let bg = [255, 255, 255], n = el
    while (n) {
      const b = parse(getComputedStyle(n).backgroundColor)
      if (b && b.a > 0.9) { bg = b.rgb; break }
      n = n.parentElement
    }
    const size = parseFloat(cs.fontSize)
    const large = size >= 24 || (size >= 18.66 && Number(cs.fontWeight) >= 700)
    const need = large ? 3 : 4.5
    const got = ratio(fg.rgb, bg)
    if (got < need - 0.01) {
      bad.push({
        text: el.textContent.trim().slice(0, 30),
        fg: cs.color, bg: 'rgb(' + bg + ')',
        got: Math.round(got * 100) / 100, need,
      })
    }
  }
  return bad
})()`

/** A one-line summary of the worst offenders, for a check's `extra` field. */
function describe(bad) {
  const seen = new Map()
  for (const b of bad) {
    const k = `${b.fg}|${b.bg}`
    if (!seen.has(k)) seen.set(k, b)
  }
  return [...seen.values()]
    .sort((a, b) => a.got - b.got)
    .slice(0, 3)
    .map(b => `${b.got}:1 (need ${b.need}) ${b.fg} on ${b.bg} — ${JSON.stringify(b.text)}`)
    .join('; ')
}

module.exports = { CONTRAST_AUDIT, describe }
