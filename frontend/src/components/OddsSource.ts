/**
 * How an odds source is described to a reader.
 *
 * ESPN's feed reports whichever sportsbook priced a game, so the raw value can
 * be "DraftKings" or "ESPN BET". Printing that alone reads as though StatEdge
 * has a relationship with that book, which it does not — there is no
 * integration, no partnership and no data agreement with any sportsbook.
 *
 * The honest form names the feed we actually use and the book only as where
 * the number originated.
 */
export function oddsSourceLabel(provider?: string | null): string {
  const book = (provider ?? '').trim()
  if (!book || /^espn$/i.test(book)) return 'ESPN'
  return `ESPN (${book} line)`
}

/** The longer sentence, for footers and methodology copy. */
export function oddsSourceSentence(provider?: string | null): string {
  const book = (provider ?? '').trim()
  if (!book || /^espn$/i.test(book)) {
    return 'Lines from ESPN’s public feed.'
  }
  return `Lines from ESPN’s public feed, which reports this game priced by ${book}. StatEdge has no relationship with that sportsbook.`
}
