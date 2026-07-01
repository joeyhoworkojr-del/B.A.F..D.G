"""Soccer and NFL prediction endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.api.schemas import (
    NFLPredictRequest,
    NFLPredictResponse,
    PlayerPropOut,
    RankedTeam,
    RankingsResponse,
    SimOut,
    SoccerPredictRequest,
    SoccerPredictResponse,
    TeamInfo,
    TotalsOut,
    WDLProbs,
    WhyFactorOut,
)
from src.data.world_cup import (
    TEAMS as WC_TEAMS,
    R16_FIXTURES,
    TOP_SCORERS,
    all_teams_sorted,
    get_scorers_for_team,
    get_team,
)
from src.data.nfl import NFL_TEAMS, all_nfl_teams_sorted, get_nfl_team
from src.predict.soccer import predict_match
from src.predict.gridiron import predict_nfl_game
from src.simulate.monte_carlo import simulate_soccer

router = APIRouter()


# ─── Soccer ───────────────────────────────────────────────────────────────────

@router.get("/teams/soccer", response_model=list[TeamInfo], tags=["Teams"])
def list_soccer_teams() -> list[TeamInfo]:
    return [
        TeamInfo(
            code=t.code, name=t.name, flag=t.flag, elo=t.elo,
            group=t.group, is_host=t.is_host,
        )
        for t in all_teams_sorted()
    ]


@router.post("/predict/soccer", response_model=SoccerPredictResponse, tags=["Predictions"])
def predict_soccer(req: SoccerPredictRequest) -> SoccerPredictResponse:
    home_code = req.home.upper()
    away_code = req.away.upper()

    try:
        home_t = get_team(home_code)
        away_t = get_team(away_code)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    # Find SR reference probs if a live fixture matches
    sr_hw = sr_dr = sr_aw = None
    for fix in R16_FIXTURES:
        if fix.home == home_code and fix.away == away_code:
            sr_hw, sr_dr, sr_aw = fix.sr_home_win, fix.sr_draw, fix.sr_away_win
            break

    scorers = get_scorers_for_team(home_code) + get_scorers_for_team(away_code)

    result = predict_match(
        home_code, away_code,
        home_t.elo, away_t.elo,
        home_is_host=home_t.is_host,
        neutral=req.neutral,
        defensive_dampener=req.defensive_dampener,
        sr_home_win=sr_hw,
        sr_draw=sr_dr,
        sr_away_win=sr_aw,
        scorers=scorers,
    )

    sim = simulate_soccer(
        result.model_probs.home_xg,
        result.model_probs.away_xg,
        knockout=req.knockout,
    )

    return SoccerPredictResponse(
        home_team=TeamInfo(
            code=home_t.code, name=home_t.name, flag=home_t.flag,
            elo=home_t.elo, group=home_t.group, is_host=home_t.is_host,
        ),
        away_team=TeamInfo(
            code=away_t.code, name=away_t.name, flag=away_t.flag,
            elo=away_t.elo, group=away_t.group, is_host=away_t.is_host,
        ),
        model_probs=WDLProbs(
            home_win=result.model_probs.home_win,
            draw=result.model_probs.draw,
            away_win=result.model_probs.away_win,
            home_xg=result.model_probs.home_xg,
            away_xg=result.model_probs.away_xg,
        ),
        blended_probs=WDLProbs(
            home_win=result.blended_probs.home_win,
            draw=result.blended_probs.draw,
            away_win=result.blended_probs.away_win,
            home_xg=result.blended_probs.home_xg,
            away_xg=result.blended_probs.away_xg,
        ),
        totals=TotalsOut(
            over_1_5=result.totals.over_1_5,
            under_1_5=result.totals.under_1_5,
            over_2_5=result.totals.over_2_5,
            under_2_5=result.totals.under_2_5,
            over_3_5=result.totals.over_3_5,
            under_3_5=result.totals.under_3_5,
            over_4_5=result.totals.over_4_5,
            under_4_5=result.totals.under_4_5,
            btts=result.totals.btts,
            btts_no=result.totals.btts_no,
            home_over_0_5=result.totals.home_over_0_5,
            home_over_1_5=result.totals.home_over_1_5,
            home_over_2_5=result.totals.home_over_2_5,
            away_over_0_5=result.totals.away_over_0_5,
            away_over_1_5=result.totals.away_over_1_5,
            away_over_2_5=result.totals.away_over_2_5,
            most_likely_total=result.totals.most_likely_total,
            expected_scoreline=list(result.totals.expected_scoreline),
        ),
        player_props=[
            PlayerPropOut(
                name=p.name, team=p.team,
                anytime_scorer=p.anytime_scorer,
                two_plus_goals=p.two_plus_goals,
                xg=p.xg,
            )
            for p in result.player_props
        ],
        scoreline_grid=result.scoreline_grid,
        why_factors=[
            WhyFactorOut(label=f.label, value=f.value)
            for f in result.why_factors
        ],
        simulation=SimOut(
            home_wins=sim.home_wins,
            draws=sim.draws,
            away_wins=sim.away_wins,
            home_advance=sim.home_advance,
            away_advance=sim.away_advance,
            home_score_dist={str(k): v for k, v in sim.home_score_dist.items()},
            away_score_dist={str(k): v for k, v in sim.away_score_dist.items()},
            total_score_dist={str(k): v for k, v in sim.total_score_dist.items()},
            std_error=sim.std_error,
        ),
        sim_error_bound=result.sim_error_bound,
        has_sr_data=result.has_sr_data,
    )


# ─── NFL ──────────────────────────────────────────────────────────────────────

@router.get("/teams/nfl", response_model=list[TeamInfo], tags=["Teams"])
def list_nfl_teams() -> list[TeamInfo]:
    return [
        TeamInfo(
            code=t.code, name=f"{t.city} {t.name}", flag=t.flag,
            elo=t.elo, conference=t.conference, division=t.division,
        )
        for t in all_nfl_teams_sorted()
    ]


@router.post("/predict/nfl", response_model=NFLPredictResponse, tags=["Predictions"])
def predict_nfl(req: NFLPredictRequest) -> NFLPredictResponse:
    home_code = req.home.upper()
    away_code = req.away.upper()

    try:
        home_t = get_nfl_team(home_code)
        away_t = get_nfl_team(away_code)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    result = predict_nfl_game(
        home_code, away_code,
        home_t.elo, away_t.elo,
        neutral_site=req.neutral_site,
    )

    return NFLPredictResponse(
        home_team=TeamInfo(
            code=home_t.code, name=f"{home_t.city} {home_t.name}",
            flag=home_t.flag, elo=home_t.elo,
            conference=home_t.conference, division=home_t.division,
        ),
        away_team=TeamInfo(
            code=away_t.code, name=f"{away_t.city} {away_t.name}",
            flag=away_t.flag, elo=away_t.elo,
            conference=away_t.conference, division=away_t.division,
        ),
        home_win_prob=result.home_win_prob,
        away_win_prob=result.away_win_prob,
        predicted_spread=result.predicted_spread,
        home_cover_prob=result.home_cover_prob,
        away_cover_prob=result.away_cover_prob,
        total_points_estimate=result.total_points_estimate,
        why_factors=[WhyFactorOut(**f) for f in result.why_factors],
    )


# ─── Rankings ─────────────────────────────────────────────────────────────────

@router.get("/rankings/soccer", response_model=RankingsResponse, tags=["Rankings"])
def soccer_rankings() -> RankingsResponse:
    teams = [
        RankedTeam(
            rank=i + 1, code=t.code, name=t.name, flag=t.flag,
            elo=t.elo, group=t.group,
        )
        for i, t in enumerate(all_teams_sorted())
    ]
    return RankingsResponse(sport="soccer", teams=teams)


@router.get("/rankings/nfl", response_model=RankingsResponse, tags=["Rankings"])
def nfl_rankings() -> RankingsResponse:
    teams = [
        RankedTeam(
            rank=i + 1, code=t.code, name=f"{t.city} {t.name}",
            flag=t.flag, elo=t.elo, conference=t.conference,
        )
        for i, t in enumerate(all_nfl_teams_sorted())
    ]
    return RankingsResponse(sport="nfl", teams=teams)


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@router.get("/fixtures/r16", tags=["Fixtures"])
def get_r16_fixtures() -> list[dict]:
    out = []
    for f in R16_FIXTURES:
        try:
            ht = get_team(f.home)
            at = get_team(f.away)
        except KeyError:
            continue
        out.append({
            "id": f.id,
            "stage": f.stage,
            "home": {"code": f.home, "name": ht.name, "flag": ht.flag, "elo": ht.elo},
            "away": {"code": f.away, "name": at.name, "flag": at.flag, "elo": at.elo},
            "venue": f.venue,
            "kickoff": f.kickoff,
            "sr_home_win": f.sr_home_win,
            "sr_draw": f.sr_draw,
            "sr_away_win": f.sr_away_win,
        })
    return out
