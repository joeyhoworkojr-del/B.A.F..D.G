import { Link } from 'react-router-dom'

const H2 = ({ id, children }: { id: string; children: React.ReactNode }) => (
  <h2 id={id} className="scroll-mt-24 font-display text-base font-bold uppercase tracking-widest text-brand">
    {children}
  </h2>
)

/**
 * About doubles as the methodology, data-source and policy page — the footer
 * links straight to each section, so every heading carries a stable anchor.
 */
export function About() {
  return (
    <div className="mx-auto max-w-2xl space-y-8 px-4 py-8 font-body text-sm leading-relaxed text-zinc-300">
      <div>
        <h1 className="font-display text-2xl font-black text-zinc-100">About StatEdge</h1>
        <p className="mt-1 text-zinc-500">
          Model projections for NFL and college football, published next to the market
          they disagree with.
        </p>
      </div>

      <section className="space-y-3">
        <H2 id="what-it-is">What it is</H2>
        <p>
          For every NFL and FBS college football game on the board, StatEdge publishes a
          projected score, a win probability, a cover probability and an over/under
          probability, and compares each to the line a sportsbook is currently posting.
        </p>
        <p>
          It is not a sportsbook. You cannot place a bet here, no money moves through the
          site, and saving or following a game records your interest — nothing more.
        </p>
      </section>

      <section className="space-y-3">
        <H2 id="methodology">Methodology</H2>
        <p>
          Team ratings produce an expected points total for each side. Those two numbers
          give a projected score; the margin and the total are then turned into
          probabilities using the league’s historical spread of outcomes — a wider band for
          college football than for the NFL, because college results scatter more.
        </p>
        <p>
          The headline number is then pulled toward the sportsbook’s no-vig line. A closing
          line is the sharpest public estimate available, and a model that ignores it is
          usually worse, not braver. College football is anchored harder than the NFL:
          there are about 135 FBS teams and far less reliable information about most of
          them.
        </p>
        <p>
          Before any edge is claimed the model is shrunk toward a coin flip, which strips
          out over-confidence. Only disagreement that survives that shrinkage is shown, so
          “no edge on this game” is a real answer rather than a failure to load.
        </p>
        <p>
          Grades are purely the size of the remaining gap: A is 6 or more percentage points,
          B is 3.5 or more, C is 1.5 or more. A grade measures disagreement with the market,
          not confidence that a pick will win.
        </p>
      </section>

      <section className="space-y-3">
        <H2 id="results">How results are recorded</H2>
        <p>
          A scheduled job on the server snapshots each game’s prediction before kickoff and
          freezes it with the model version and the market line at that moment. When the
          game finishes it is graded against that snapshot. Loading a page never creates or
          changes a prediction, and a newer model cannot rewrite one that is already open.
        </p>
        <p>
          Live in-game probabilities are recalculated while a game runs, but they are never
          stored or graded — scoring a probability after the score is known would flatter
          the record. See the{' '}
          <Link to="/results" className="font-semibold text-brand hover:underline">full results</Link>.
        </p>
      </section>

      <section className="space-y-3">
        <H2 id="limits">Honest limits</H2>
        <ul className="list-inside list-disc space-y-1.5 text-zinc-400">
          <li>Nothing public reliably beats a closing line, and StatEdge does not claim to.</li>
          <li>The graded sample is small. Football seasons are short and streaks are mostly noise.</li>
          <li>Lines come from one provider. StatEdge does not shop prices across books.</li>
          <li>Where the feed omits a price, −110 is assumed — and labelled as an assumption.</li>
          <li>Player props are not available; there is no props data source configured.</li>
        </ul>
      </section>

      <section className="space-y-3">
        <H2 id="data-sources">Data sources</H2>
        <ul className="list-inside list-disc space-y-1.5 text-zinc-400">
          <li>ESPN public site API — scores, schedules, play-by-play, posted lines and headlines</li>
          <li>Open-Meteo — stadium weather forecasts</li>
          <li>League-calibrated power ratings for NFL and FBS college football</li>
        </ul>
        <p className="text-zinc-400">
          News headlines link back to the publisher. StatEdge shows the headline and the
          publisher’s own summary line only, and never republishes a full article. The model
          does not read news stories, so nothing on the site claims a headline moved a
          projection.
        </p>
      </section>

      <section className="space-y-3">
        <H2 id="privacy">Privacy</H2>
        <p>
          There are no accounts, so StatEdge holds no personal data — no names, no email
          addresses, no passwords. Nothing you do here is tied to an identity.
        </p>
        <p>
          Two small preferences are kept in your own browser: which notifications you have
          already seen, and lightweight UI state. That data stays on your device, is never
          sent to the server, and clearing your browser data removes it.
        </p>
      </section>

      <section className="space-y-3">
        <H2 id="terms">Terms</H2>
        <p>
          StatEdge is provided for information only. Projections are estimates and can be
          wrong. Nothing here is betting advice, and StatEdge does not accept, place,
          process or forward wagers.
        </p>
        <p>
          If you gamble, set limits and stick to them. In the US, the National Problem
          Gambling Helpline is 1-800-522-4700.
        </p>
      </section>

      <p className="border-t border-terminal-border pt-4 text-xs text-zinc-500">
        Questions about any of this are answered in more detail in the{' '}
        <Link to="/faq" className="font-semibold text-brand hover:underline">FAQ</Link>.
      </p>
    </div>
  )
}
