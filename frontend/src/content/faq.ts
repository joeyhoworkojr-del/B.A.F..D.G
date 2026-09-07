/**
 * FAQ content.
 *
 * One source of truth, shared by the /faq page and the homepage preview, so the
 * two can never drift. Every answer describes what StatEdge actually does today
 * — where a feature is missing, the answer says so rather than promising it.
 */

export interface FaqEntry {
  id: string          // stable anchor, used for shareable links
  q: string
  a: string[]         // paragraphs
  category: FaqCategory
}

export type FaqCategory =
  | 'Getting started'
  | 'The model'
  | 'Markets & odds'
  | 'Live games'
  | 'Track record'
  | 'Accounts & pricing'
  | 'Data & sources'

export const FAQ_CATEGORIES: FaqCategory[] = [
  'Getting started',
  'The model',
  'Markets & odds',
  'Live games',
  'Track record',
  'Accounts & pricing',
  'Data & sources',
]

export const FAQ: FaqEntry[] = [
  // ── Getting started ────────────────────────────────────────────────────────
  {
    id: 'what-is-statedge',
    category: 'Getting started',
    q: 'What is StatEdge?',
    a: [
      'StatEdge is a prediction site for NFL and college football. For every game on the board it publishes a projected score, a win probability, a cover probability and an over/under probability, and it compares each of those to the line the market is currently posting.',
      'It is not a sportsbook. You cannot place a bet here, no money moves through the site, and nothing you do on StatEdge is a wager.',
    ],
  },
  {
    id: 'is-it-free',
    category: 'Getting started',
    q: 'Is StatEdge free?',
    a: [
      'Yes. Everything implemented on the site is available to everyone right now, and no payment method is collected anywhere. There is no checkout, no trial and no upsell.',
      'The server decides what each visitor can access at /api/v1/entitlements, and today that answer is "the free plan, with every implemented feature included".',
    ],
  },
  {
    id: 'which-sports',
    category: 'Getting started',
    q: 'Which sports and leagues are covered?',
    a: [
      'NFL and NCAA college football (FBS). The engine has code for other sports from an earlier version of the product, but nothing else is exposed, modelled or supported.',
    ],
  },
  {
    id: 'how-to-read-a-game',
    category: 'Getting started',
    q: 'How do I read a game page?',
    a: [
      'The top card is the single strongest disagreement between the model and the market for that game — the selection, the price, the model\'s probability, the book\'s no-vig probability, and the gap between them in percentage points.',
      'Below that, the Markets panel lets you compare moneyline, spread and total side by side. "Why this edge?" explains, in words, how that specific number was built.',
    ],
  },

  // ── The model ──────────────────────────────────────────────────────────────
  {
    id: 'how-the-model-works',
    category: 'The model',
    q: 'How does the model work?',
    a: [
      'Team ratings produce an expected points total for each side. Those two numbers give a projected score, and the margin and total are turned into probabilities using the league\'s historical spread of outcomes — roughly 16.5 points of margin variance for college football and a tighter band for the NFL.',
      'The result is then pulled toward the sportsbook\'s no-vig line, because a closing line is the sharpest public estimate available and pretending otherwise costs accuracy. College football is anchored harder than the NFL, because there are about 135 FBS teams and far less reliable information about most of them.',
    ],
  },
  {
    id: 'why-agree-with-market',
    category: 'The model',
    q: 'Why does the model so often agree with the market?',
    a: [
      'Because the market is good. A closing line is the aggregate of a lot of informed money, and a model that disagrees with it constantly is usually wrong rather than sharp.',
      'StatEdge deliberately shrinks its own confidence toward a coin flip before any edge is claimed, so only disagreements that survive that shrinkage are shown. "No edge on this game" is a real answer, not a failure to load.',
    ],
  },
  {
    id: 'what-is-an-edge',
    category: 'The model',
    q: 'What does "edge" mean here?',
    a: [
      'Edge is the gap, in percentage points of probability, between the model\'s number and the sportsbook\'s number with the vig removed. A model probability of 57% against a no-vig book probability of 52% is a 5-point edge.',
      'It is not a price difference and it is not an expected profit. It is a disagreement about how likely something is.',
    ],
  },
  {
    id: 'grades',
    category: 'The model',
    q: 'What do the A / B / C grades mean?',
    a: [
      'They are purely the size of that probability gap: A is 6 or more percentage points, B is 3.5 or more, C is 1.5 or more, and anything smaller is shown as no edge.',
      'A grade measures how much the model disagrees with the market. It is not a confidence rating, a guarantee, or a claim that the pick will win.',
    ],
  },
  {
    id: 'model-version',
    category: 'The model',
    q: 'What is the model version on each page?',
    a: [
      'Every stored prediction records the version of the model that produced it. A newer model cannot silently rewrite an open prediction, so the track record always reflects what was actually published at the time.',
    ],
  },
  {
    id: 'injuries-and-weather',
    category: 'The model',
    q: 'Does the model account for injuries and weather?',
    a: [
      'Weather and recorded lineup availability are applied as explicit adjustments, and any that fired are listed on the game page.',
      'News stories are not an input. The News section is reporting for you to read; it is marked "Not yet reflected in projection" because the model genuinely has not consumed it.',
    ],
  },

  // ── Markets & odds ─────────────────────────────────────────────────────────
  {
    id: 'where-odds-come-from',
    category: 'Markets & odds',
    q: 'Where do the odds come from?',
    a: [
      'From ESPN\'s public scoreboard feed, which carries the line a named provider is posting — usually ESPN BET. The provider is shown next to the numbers on every panel.',
      'StatEdge does not shop lines across books and does not claim to show the best available price.',
    ],
  },
  {
    id: 'assumed-price',
    category: 'Markets & odds',
    q: 'Why do some prices say "−110 assumed"?',
    a: [
      'The feed publishes the spread and total lines but not always the price attached to them. Where the price is missing, the standard −110 is assumed so a comparison can be made at all, and the panel says so explicitly rather than presenting an assumption as a quote.',
    ],
  },
  {
    id: 'no-vig',
    category: 'Markets & odds',
    q: 'What is a "no-vig" probability?',
    a: [
      'A sportsbook\'s two prices add up to more than 100% — the excess is the book\'s margin. Removing it proportionally gives the probabilities the book is actually implying, which is the only fair thing to compare a model against.',
    ],
  },
  {
    id: 'green-and-red',
    category: 'Markets & odds',
    q: 'What do the green and red highlights mean?',
    a: [
      'Green marks the side the model prefers on that market; red marks the side it is against. Green is used only where the model genuinely sees value — it is not decoration.',
    ],
  },
  {
    id: 'player-props',
    category: 'Markets & odds',
    q: 'Do you have player props?',
    a: [
      'Not yet, and the Props page says so rather than showing invented numbers. Two things are missing: a licensed player-props odds provider, and player-level projections from the model, which currently projects team scores and game totals only.',
    ],
  },

  // ── Live games ─────────────────────────────────────────────────────────────
  {
    id: 'live-updates',
    category: 'Live games',
    q: 'Do predictions update during a game?',
    a: [
      'Yes. Once a game is in progress the model produces a live win probability from the score, the time remaining and the pre-game expectation, and the game page shows that instead of the pre-game number.',
      'The pre-game prediction is kept separately and is what gets graded — a live update never overwrites the record.',
    ],
  },
  {
    id: 'how-fresh',
    category: 'Live games',
    q: 'How fresh is the live data?',
    a: [
      'Scores refresh about every 15 seconds and play-by-play about every 8. Every panel shows the timestamp of the data actually on your screen, and turns amber when that data is older than it should be.',
      'If a refresh fails, the last good data stays up with its original timestamp visibly ageing. Freshness is never inferred from the fact that a timer is running.',
    ],
  },
  {
    id: 'play-by-play',
    category: 'Live games',
    q: 'Why is play-by-play empty for some games?',
    a: [
      'Before kickoff there are no plays to show. During a game, some feeds populate more slowly than others; the panel says which case it is instead of showing a blank box.',
    ],
  },

  // ── Track record ───────────────────────────────────────────────────────────
  {
    id: 'how-results-are-recorded',
    category: 'Track record',
    q: 'How is the track record recorded?',
    a: [
      'A scheduled job on the server snapshots each game\'s prediction before kickoff and stores it with the model version and the market line at the time. When the game finishes it is graded against that stored snapshot.',
      'Loading a page never creates or changes a prediction, so browsing the site cannot inflate the record.',
    ],
  },
  {
    id: 'hit-rate-vs-probability',
    category: 'Track record',
    q: 'Is the historical hit rate the same as the model\'s probability?',
    a: [
      'No, and they are labelled separately for that reason. A hit rate is the share of past graded predictions that came in. A model probability is this game\'s estimate.',
      'An average over past games is not a projection for the next one, and StatEdge never presents one as the other.',
    ],
  },
  {
    id: 'brier',
    category: 'Track record',
    q: 'What is the Brier score?',
    a: [
      'A measure of how well-calibrated probabilities are, where lower is better. Always guessing a coin flip scores 0.25. It is shown alongside the sportsbook\'s own score on the same games, which is the only comparison that means anything.',
    ],
  },
  {
    id: 'sample-size',
    category: 'Track record',
    q: 'How much should I read into the record?',
    a: [
      'Not much yet. Football seasons are short and the graded sample is small, so a run of good or bad results is mostly noise. The record is published in full, including the periods where the model has been behind the market.',
    ],
  },

  // ── Accounts & pricing ─────────────────────────────────────────────────────
  {
    id: 'accounts',
    category: 'Accounts & pricing',
    q: 'Can I create an account?',
    a: [
      'Not yet. There is no sign-in on the site, and there is no fake one either — no form that stores a password, and nothing in your browser pretending to be a login.',
      'Accounts need two things StatEdge does not have configured: an identity provider that manages credentials properly, and durable storage that survives a deploy. Until both exist, adding accounts would mean losing everyone\'s data on the next release.',
    ],
  },
  {
    id: 'saving-a-game',
    category: 'Accounts & pricing',
    q: 'If I save or follow a game, have I placed a bet?',
    a: [
      'No. StatEdge does not accept, place, process or forward wagers of any kind. Saving a game records your interest so it is easier to find — nothing more.',
    ],
  },
  {
    id: 'alerts',
    category: 'Accounts & pricing',
    q: 'Can I get alerts when a new edge appears?',
    a: [
      'Only in the app. The notification centre in the header lists the graded edges the model is publishing right now, and read state is kept on your device.',
      'Push and email alerts need a signed-in account, so they are not available.',
    ],
  },
  {
    id: 'will-there-be-pro',
    category: 'Accounts & pricing',
    q: 'Will there be a paid plan?',
    a: [
      'Possibly, later. The plan structure exists on the server so features can be split cleanly when there is something worth charging for, but nothing is being sold today and no billing code runs on the site.',
    ],
  },

  // ── Data & sources ─────────────────────────────────────────────────────────
  {
    id: 'data-sources',
    category: 'Data & sources',
    q: 'Where does the data come from?',
    a: [
      'Scores, schedules, play-by-play, betting lines and headlines all come from ESPN\'s public site API. Weather comes from Open-Meteo.',
      'Each panel names its source next to the numbers, so you can always tell what you are looking at.',
    ],
  },
  {
    id: 'news-attribution',
    category: 'Data & sources',
    q: 'Do you republish full articles?',
    a: [
      'No. The News section shows the headline, the publisher\'s own one-line summary, the byline and a link back to the original. The full story stays at the source.',
    ],
  },
  {
    id: 'ai-written',
    category: 'Data & sources',
    q: 'Is any of this written by AI?',
    a: [
      'The explanations on game pages are generated from the model\'s recorded inputs — they describe numbers that actually exist in the prediction, not a narrative invented around them.',
      'StatEdge does not generate reporting, quotes, or causal explanations for why something happened.',
    ],
  },
  {
    id: 'accuracy-claims',
    category: 'Data & sources',
    q: 'Do you claim to beat the market?',
    a: [
      'No. Nothing public reliably beats a closing line, and StatEdge does not claim to. What it offers is a transparent second opinion with its full record attached, including where it has been wrong.',
    ],
  },
  {
    id: 'contact',
    category: 'Data & sources',
    q: 'How do I report a problem or ask a question?',
    a: [
      'StatEdge is a personal project without a support desk. Issues are tracked in the project repository, which is the fastest way to get something looked at.',
    ],
  },
]

export const FAQ_PREVIEW_IDS = [
  'what-is-statedge',
  'what-is-an-edge',
  'why-agree-with-market',
  'is-it-free',
]
