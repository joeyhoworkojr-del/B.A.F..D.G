"""
Measure the model against the market, on real completed games.

    python -m tools.backtest spread      # game lines vs the closing line
    python -m tools.backtest props       # prop calibration by market
    python -m tools.backtest all

This exists because "the estimates feel poor" is not something anyone can act
on, and because an accuracy claim that is not reproducible is not an accuracy
claim. Every number StatEdge publishes about its own accuracy should come from
a command anyone can re-run.

Two rules it follows, and both matter:

  * Walk-forward only. Priors for week W are built from weeks already played,
    and a game's result is fed to the self-correcting ratings only after every
    game in its week has been predicted. No market line is passed into the
    model, so it produces its own number.

  * The market is the baseline, not the model. A model that cannot beat the
    closing line is not adding anything, and the output is arranged to make
    that visible rather than to flatter.

Data is nflverse's published history, cached under `.backtest/` after the first
run. The game file carries the closing spread, total and moneylines, which is
what makes a fair comparison possible at all.
"""
from __future__ import annotations

import asyncio
import csv
import logging
import math
import os
import sys
import urllib.request
from collections import defaultdict
from typing import Optional

logging.disable(logging.ERROR)

CACHE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".backtest")
GAMES_URL = "https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv"
RELEASE = "https://github.com/nflverse/nflverse-data/releases/download"
SEASONS = [2022, 2023, 2024, 2025, 2026]

# Enough games played for an in-season EPA prior to carry any information.
MIN_WEEK = 5
# Enough of a player's own log to project from.
MIN_PRIOR_GAMES = 4

# nflverse spells a few franchises differently from this app.
ALIAS = {"LA": "LAR", "OAK": "LV", "SD": "LAC", "STL": "LAR", "WSH": "WAS"}

PROP_MARKETS = {
    "pass_yards": "passing_yards", "pass_attempts": "attempts",
    "pass_tds": "passing_tds", "rush_yards": "rushing_yards",
    "carries": "carries", "rush_tds": "rushing_tds",
    "rec_yards": "receiving_yards", "receptions": "receptions",
    "rec_tds": "receiving_tds",
}


def _code(team: str) -> str:
    return ALIAS.get(team, team)


def _fetch(url: str, name: str) -> Optional[str]:
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, name)
    if os.path.exists(path) and os.path.getsize(path) > 1000:
        return open(path, encoding="utf-8").read()
    try:
        with urllib.request.urlopen(url, timeout=120) as resp:
            body = resp.read().decode("utf-8", "replace")
    except Exception as exc:
        print(f"  could not fetch {name}: {type(exc).__name__}", file=sys.stderr)
        return None
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(body)
    return body


def _num(raw: str) -> Optional[float]:
    raw = (raw or "").strip()
    if not raw or raw.upper() in ("NA", "NAN", "NULL"):
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _rmse(errs: list[float]) -> float:
    return math.sqrt(sum(e * e for e in errs) / len(errs))


def _mae(errs: list[float]) -> float:
    return sum(abs(e) for e in errs) / len(errs)


def _line(name: str, errs: list[float]) -> str:
    if not errs:
        return f"{name:<28} no data"
    return (f"{name:<28} n={len(errs):<5} MAE {_mae(errs):5.2f}  "
            f"RMSE {_rmse(errs):5.2f}  bias {sum(errs)/len(errs):+5.2f}")


# ─── Game lines ──────────────────────────────────────────────────────────────

def _load_games():
    from src.data import nfl as nfl_data

    text = _fetch(GAMES_URL, "games.csv")
    if not text:
        return []
    out = []
    for r in csv.DictReader(text.splitlines()):
        if r.get("game_type") != "REG" or int(r.get("season") or 0) not in SEASONS:
            continue
        margin, spread = _num(r.get("result")), _num(r.get("spread_line"))
        if margin is None or spread is None:
            continue
        home, away = _code(r["home_team"]), _code(r["away_team"])
        if home not in nfl_data.NFL_TEAMS or away not in nfl_data.NFL_TEAMS:
            continue
        out.append({
            "season": int(r["season"]), "week": int(r["week"]),
            "home": home, "away": away, "margin": margin,
            "total": _num(r.get("total")),
            # nflverse quotes `spread_line` as the home team's expected margin,
            # the same convention the model's `predicted_spread` uses.
            "mkt_spread": spread, "mkt_total": _num(r.get("total_line")),
            "home_ml": _num(r.get("home_moneyline")),
            "away_ml": _num(r.get("away_moneyline")),
        })
    return out


def _install_priors(season: int, upto_week: int, weeks_by_season) -> int:
    from src.data import nfl as nfl_data
    from src.ingest import nflverse
    from src.predict import priors

    rows = [r for r in weeks_by_season.get(season, [])
            if r.season_type == "REG" and r.week < upto_week]
    forms = nflverse.team_form(nflverse.NflverseData(season=season, ok=bool(rows), teams=rows))
    teams = {}
    for raw, form in forms.items():
        code = _code(raw)
        if code not in nfl_data.NFL_TEAMS:
            continue
        if form.off_epa_per_game is None or form.def_epa_per_game is None:
            continue
        teams[code] = priors.TeamPrior(
            code=code, points=form.off_epa_per_game - form.def_epa_per_game,
            games=form.games, source="nflverse-epa")
    priors._priors["nfl"] = priors.LeaguePriors(
        league="nfl", ok=bool(teams), source="nflverse-epa",
        fetched_at="backtest", teams=priors._centre(teams) if teams else {})
    return len(teams)


async def run_spread() -> None:
    from src.api.routes.predictions import (
        _effective_elo, _no_vig_home_prob, _predict_gridiron,
    )
    from src.api.schemas import NFLPredictRequest
    from src.ingest import nflverse
    from src.track import ratings

    games = _load_games()
    if not games:
        print("no game history available")
        return

    weeks = {}
    for season in SEASONS:
        text = _fetch(f"{RELEASE}/stats_team/stats_team_week_{season}.csv",
                      f"team_{season}.csv")
        if text:
            weeks[season] = nflverse.parse_team_weeks(text)

    by_week = defaultdict(list)
    for g in games:
        by_week[(g["season"], g["week"])].append(g)

    spread_model, spread_market, spread_blend = [], [], []
    total_model, total_market = [], []
    prob_model, prob_market = [], []
    ats = []
    ratings.reset()

    for key in sorted(by_week):
        season, week = key
        if week < MIN_WEEK or _install_priors(season, week, weeks) == 0:
            continue
        elos = {}
        for g in by_week[key]:
            try:
                pred = await _predict_gridiron(
                    NFLPredictRequest(home=g["home"], away=g["away"],
                                      apply_weather=False, apply_lineups=False),
                    "nfl")
            except Exception:
                continue
            elos[g["home"]] = _effective_elo("nfl", g["home"])
            elos[g["away"]] = _effective_elo("nfl", g["away"])

            spread_model.append(pred.predicted_spread - g["margin"])
            spread_market.append(g["mkt_spread"] - g["margin"])
            from src.api.routes.predictions import _model_weight
            w = _model_weight("nfl")
            spread_blend.append(
                w * pred.predicted_spread + (1 - w) * g["mkt_spread"] - g["margin"])

            if g["total"] is not None:
                total_model.append(pred.total_points_estimate - g["total"])
                if g["mkt_total"] is not None:
                    total_market.append(g["mkt_total"] - g["total"])

            if g["margin"] != 0:
                won = 1.0 if g["margin"] > 0 else 0.0
                prob_model.append((pred.home_win_prob, won))
                if g["home_ml"] and g["away_ml"]:
                    class _G:
                        market_home_ml, market_away_ml = g["home_ml"], g["away_ml"]
                    mp = _no_vig_home_prob(_G())
                    if mp is not None:
                        prob_market.append((mp, won))

            diff = pred.predicted_spread - g["mkt_spread"]
            edge = g["margin"] - g["mkt_spread"]
            if abs(diff) >= 1.0 and edge != 0:
                ats.append(1.0 if (edge > 0) == (diff > 0) else 0.0)

        # Results reach the ratings only once the whole week is predicted.
        for g in by_week[key]:
            if g["margin"] == 0 or g["home"] not in elos or g["away"] not in elos:
                continue
            hs = 1 if g["margin"] > 0 else 0
            ratings.record_result("nfl", g["home"], g["away"],
                                  elos[g["home"]], elos[g["away"]], hs, 1 - hs)

    print(f"{len(spread_model)} walk-forward games, {SEASONS[0]}-{SEASONS[-1]}\n")
    print("── Spread: predicted home margin vs actual ──")
    print(_line("StatEdge model alone", spread_model))
    print(_line("Market closing line", spread_market))
    print(_line("Published blend", spread_blend))
    print("\n── Total points ──")
    print(_line("StatEdge model alone", total_model))
    print(_line("Market closing total", total_market))

    def brier(pairs):
        return sum((p - o) ** 2 for p, o in pairs) / len(pairs) if pairs else None

    print("\n── Home win probability (Brier; 0.25 is a coin flip) ──")
    for name, pairs in (("StatEdge model", prob_model), ("Market no-vig", prob_market)):
        b = brier(pairs)
        if b is not None:
            print(f"{name:<28} n={len(pairs):<5} Brier {b:.4f}")

    if ats:
        print("\n── Where the model disagreed with the line by 1+ point ──")
        print(f"{'StatEdge side ATS':<28} n={len(ats):<5} "
              f"{sum(ats)/len(ats)*100:.1f}%   (52.4% needed at -110)")


# ─── Player props ────────────────────────────────────────────────────────────

def _load_player_history():
    hist = defaultdict(list)
    for season in SEASONS:
        text = _fetch(f"{RELEASE}/stats_player/stats_player_week_{season}.csv",
                      f"player_{season}.csv")
        if not text:
            continue
        for row in csv.DictReader(text.splitlines()):
            if (row.get("season_type") or "REG").upper() != "REG":
                continue
            pid = row.get("player_id") or ""
            if not pid:
                continue
            hist[pid].append((
                int(row["season"]), int(row["week"]),
                {m: (_num(row.get(col)) or 0.0) for m, col in PROP_MARKETS.items()},
            ))
    for pid in hist:
        hist[pid].sort(key=lambda r: (r[0], r[1]))
    return hist


def run_props() -> None:
    from src.predict import player_props as pp

    hist = _load_player_history()
    if not hist:
        print("no player history available")
        return

    errs = defaultdict(list)
    buckets = defaultdict(list)
    per_market = defaultdict(list)

    for games in hist.values():
        for i in range(MIN_PRIOR_GAMES, len(games)):
            past, (_, _, actual) = games[:i], games[i]
            for market in PROP_MARKETS:
                samples = [g[2][market] for g in past]
                if len(samples) < MIN_PRIOR_GAMES:
                    continue
                mean = sum(samples) / len(samples)
                if mean < pp._MIN_PUBLISHABLE.get(market, 0.0):
                    continue
                base, _, _ = pp._form_blend(mean, samples)
                proj = round(base, 1)
                if proj <= 0:
                    continue
                sigma, _, _ = pp.sigma_for(proj, market, samples)
                if sigma is None:
                    continue
                got = actual[market]
                errs[market].append(proj - got)
                for offset in (-0.25, -0.1, 0.0, 0.1, 0.25):
                    line = round(proj * (1 + offset), 1)
                    if line <= 0:
                        continue
                    p = pp.over_probability(proj, line, market, sigma=sigma)
                    if p is None:
                        continue
                    went = 1.0 if got > line else 0.0
                    buckets[min(int(p * 10), 9)].append((p, went))
                    per_market[market].append((p, went))

    print("── Projection accuracy (projection − actual) ──")
    print(f"{'market':<16}{'n':>7}{'MAE':>9}{'RMSE':>9}{'bias':>9}")
    for market in PROP_MARKETS:
        e = errs[market]
        if len(e) < 200:
            continue
        print(f"{market:<16}{len(e):>7}{_mae(e):>9.2f}{_rmse(e):>9.2f}"
              f"{sum(e)/len(e):>+9.2f}")

    print("\n── Calibration of P(over): what we said against what happened ──")
    print(f"{'said':>9}{'happened':>11}{'n':>9}{'gap':>8}")
    gaps = n_tot = 0.0
    for b in range(10):
        rows = buckets[b]
        if len(rows) < 50:
            continue
        said = sum(p for p, _ in rows) / len(rows)
        got = sum(o for _, o in rows) / len(rows)
        print(f"{said*100:>8.1f}%{got*100:>10.1f}%{len(rows):>9}{(got-said)*100:>+8.1f}")
        gaps += abs(got - said) * len(rows)
        n_tot += len(rows)
    if n_tot:
        print(f"\nmean absolute calibration error: {gaps/n_tot*100:.1f} points")

    print("\n── By market, with the family each one uses ──")
    from src.predict import distributions
    print(f"{'market':<16}{'family':>10}{'n':>9}{'cal error':>12}")
    for market, rows in per_market.items():
        b = defaultdict(list)
        for p, o in rows:
            b[min(int(p * 10), 9)].append((p, o))
        g = n = 0.0
        for rs in b.values():
            if len(rs) < 30:
                continue
            said = sum(p for p, _ in rs) / len(rs)
            got = sum(o for _, o in rs) / len(rs)
            g += abs(got - said) * len(rs)
            n += len(rs)
        if n:
            print(f"{market:<16}{distributions.family_for(market):>10}"
                  f"{int(n):>9}{g/n*100:>11.1f}p")


def main() -> None:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    what = (sys.argv[1] if len(sys.argv) > 1 else "all").lower()
    if what in ("spread", "all"):
        print("=" * 68)
        print("GAME LINES")
        print("=" * 68)
        asyncio.run(run_spread())
        print()
    if what in ("props", "all"):
        print("=" * 68)
        print("PLAYER PROPS")
        print("=" * 68)
        run_props()


if __name__ == "__main__":
    main()
