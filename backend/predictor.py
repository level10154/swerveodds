"""Prediction engine using recent form + Poisson goal model.
Produces: 1X2 probabilities, BTTS %, Over 2.5 %, most likely correct score,
plus confidence and pick.
"""
import math
from typing import Any

HOME_ADVANTAGE = 0.35  # xG-ish boost for home


def _team_form_stats(matches: list[dict], team_id: int, limit: int = 10) -> dict:
    """Compute avg goals scored/conceded, points per game from finished matches."""
    played = 0
    gs = 0
    gc = 0
    pts = 0
    wins = 0
    draws = 0
    losses = 0
    btts_count = 0
    over25_count = 0
    form_letters: list[str] = []
    for m in matches[:limit]:
        if m.get("status") != "FINISHED":
            continue
        home = m["homeTeam"]["id"]
        away = m["awayTeam"]["id"]
        ft = m.get("score", {}).get("fullTime", {})
        hs = ft.get("home")
        as_ = ft.get("away")
        if hs is None or as_ is None:
            continue
        played += 1
        is_home = home == team_id
        my = hs if is_home else as_
        opp = as_ if is_home else hs
        gs += my
        gc += opp
        if hs > 0 and as_ > 0:
            btts_count += 1
        if hs + as_ > 2.5:
            over25_count += 1
        if my > opp:
            pts += 3
            wins += 1
            form_letters.append("W")
        elif my == opp:
            pts += 1
            draws += 1
            form_letters.append("D")
        else:
            losses += 1
            form_letters.append("L")
    if played == 0:
        return {
            "played": 0, "gs_avg": 1.3, "gc_avg": 1.3, "ppg": 1.3,
            "wins": 0, "draws": 0, "losses": 0,
            "btts_pct": 50, "over25_pct": 50, "form": [],
        }
    return {
        "played": played,
        "gs_avg": round(gs / played, 2),
        "gc_avg": round(gc / played, 2),
        "ppg": round(pts / played, 2),
        "wins": wins, "draws": draws, "losses": losses,
        "btts_pct": round(btts_count / played * 100),
        "over25_pct": round(over25_count / played * 100),
        "form": form_letters,
    }


def _poisson(k: int, lam: float) -> float:
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return math.exp(-lam) * (lam ** k) / math.factorial(k)


def predict(home_matches: list[dict], away_matches: list[dict], home_id: int, away_id: int) -> dict:
    hs = _team_form_stats(home_matches, home_id)
    as_ = _team_form_stats(away_matches, away_id)

    # Expected goals: attack strength (own gs) vs opponent defence (opp gc), + home advantage.
    lam_home = max(0.2, (hs["gs_avg"] + as_["gc_avg"]) / 2 + HOME_ADVANTAGE)
    lam_away = max(0.15, (as_["gs_avg"] + hs["gc_avg"]) / 2)

    max_g = 6
    p_home_win = 0.0
    p_draw = 0.0
    p_away_win = 0.0
    p_btts = 0.0
    p_over25 = 0.0
    p_over15 = 0.0
    p_over35 = 0.0
    score_probs = {}
    for i in range(max_g + 1):
        for j in range(max_g + 1):
            p = _poisson(i, lam_home) * _poisson(j, lam_away)
            score_probs[f"{i}-{j}"] = p
            if i > j:
                p_home_win += p
            elif i == j:
                p_draw += p
            else:
                p_away_win += p
            if i > 0 and j > 0:
                p_btts += p
            if i + j > 1.5:
                p_over15 += p
            if i + j > 2.5:
                p_over25 += p
            if i + j > 3.5:
                p_over35 += p

    # Normalise 1X2 (rounding)
    total = p_home_win + p_draw + p_away_win
    if total > 0:
        p_home_win /= total
        p_draw /= total
        p_away_win /= total

    # Top likely correct scores
    top_scores = sorted(score_probs.items(), key=lambda x: -x[1])[:5]
    top_scores_out = [{"score": s, "prob": round(p * 100, 1)} for s, p in top_scores]
    most_likely = top_scores_out[0] if top_scores_out else {"score": "1-1", "prob": 10}

    # Pick
    outcomes = [("HOME", p_home_win), ("DRAW", p_draw), ("AWAY", p_away_win)]
    outcomes.sort(key=lambda x: -x[1])
    pick_code, pick_prob = outcomes[0]

    confidence = round(pick_prob * 100)
    # Recommended bet: choose highest edge among 1X2 / Over2.5 / BTTS
    candidates = [
        {"market": "1X2", "pick": pick_code, "prob": pick_prob},
        {"market": "Over 2.5 Goals", "pick": "YES" if p_over25 > 0.5 else "NO",
         "prob": p_over25 if p_over25 > 0.5 else 1 - p_over25},
        {"market": "BTTS", "pick": "YES" if p_btts > 0.5 else "NO",
         "prob": p_btts if p_btts > 0.5 else 1 - p_btts},
    ]
    candidates.sort(key=lambda x: -x["prob"])
    best = candidates[0]

    return {
        "home_form": hs,
        "away_form": as_,
        "lambda_home": round(lam_home, 2),
        "lambda_away": round(lam_away, 2),
        "probs": {
            "home": round(p_home_win * 100, 1),
            "draw": round(p_draw * 100, 1),
            "away": round(p_away_win * 100, 1),
            "btts_yes": round(p_btts * 100, 1),
            "btts_no": round((1 - p_btts) * 100, 1),
            "over_15": round(p_over15 * 100, 1),
            "over_25": round(p_over25 * 100, 1),
            "over_35": round(p_over35 * 100, 1),
            "under_25": round((1 - p_over25) * 100, 1),
        },
        "top_scores": top_scores_out,
        "most_likely_score": most_likely,
        "pick": pick_code,
        "confidence": confidence,
        "best_bet": {
            "market": best["market"],
            "pick": best["pick"],
            "confidence": round(best["prob"] * 100),
        },
    }
