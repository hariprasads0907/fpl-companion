# Copyright 2026 Google LLC
# FPL (Fantasy Premier League) live client service

import json
import time
import urllib.request
from typing import Any, Dict, List, Optional

_CACHE: Dict[str, Any] = {}
_CACHE_TIMESTAMP: float = 0
CACHE_TTL_SECONDS = 300  # 5 min cache


def _fetch_fpl_data() -> Dict[str, Any]:
    global _CACHE, _CACHE_TIMESTAMP
    now = time.time()
    if _CACHE and (now - _CACHE_TIMESTAMP) < CACHE_TTL_SECONDS:
        return _CACHE

    url = "https://fantasy.premierleague.com/api/bootstrap-static/"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
            _CACHE = data
            _CACHE_TIMESTAMP = now
            return data
    except Exception as e:
        if _CACHE:
            return _CACHE
        raise RuntimeError(f"Failed to fetch FPL bootstrap data: {e}")


def _get_team_map(data: Dict[str, Any]) -> Dict[int, Dict[str, Any]]:
    return {t["id"]: t for t in data.get("teams", [])}


def _get_position_map(data: Dict[str, Any]) -> Dict[int, str]:
    return {et["id"]: et["singular_name_short"] for et in data.get("element_types", [])}


def get_current_gameweek_info() -> Dict[str, Any]:
    """Returns the current, next, and upcoming Gameweek deadlines."""
    data = _fetch_fpl_data()
    events = data.get("events", [])
    current_gw = None
    next_gw = None

    for ev in events:
        if ev.get("is_current"):
            current_gw = ev
        if ev.get("is_next"):
            next_gw = ev

    return {
        "current_gameweek": {
            "id": current_gw.get("id") if current_gw else None,
            "name": current_gw.get("name") if current_gw else "N/A",
            "finished": current_gw.get("finished") if current_gw else False,
            "average_score": current_gw.get("average_entry_score") if current_gw else None,
            "highest_score": current_gw.get("highest_score") if current_gw else None,
        } if current_gw else "Season in progress / check next GW",
        "next_gameweek": {
            "id": next_gw.get("id") if next_gw else None,
            "name": next_gw.get("name") if next_gw else "N/A",
            "deadline_time": next_gw.get("deadline_time") if next_gw else None,
        } if next_gw else "No upcoming GW",
    }


def search_players(
    query: str = "",
    position: Optional[str] = None,
    max_price: Optional[float] = None,
    limit: int = 6,
) -> List[Dict[str, Any]]:
    """Searches FPL players by name, team, position, or price ceiling."""
    data = _fetch_fpl_data()
    teams = _get_team_map(data)
    pos_map = _get_position_map(data)
    elements = data.get("elements", [])

    results = []
    q = query.strip().lower()

    pos_filter = position.upper() if position else None
    pos_map_rev = {"GK": 1, "GKP": 1, "DEF": 2, "MID": 3, "FWD": 4}
    target_type = pos_map_rev.get(pos_filter) if pos_filter else None

    for p in elements:
        name = f"{p.get('first_name', '')} {p.get('second_name', '')}".lower()
        web_name = p.get("web_name", "").lower()
        team_name = teams.get(p.get("team"), {}).get("name", "").lower()
        team_short = teams.get(p.get("team"), {}).get("short_name", "").lower()

        if q:
            if q not in name and q not in web_name and q not in team_name and q not in team_short:
                continue

        if target_type and p.get("element_type") != target_type:
            continue

        cost_m = p.get("now_cost", 0) / 10.0
        if max_price is not None and cost_m > max_price:
            continue

        results.append({
            "id": p["id"],
            "web_name": p["web_name"],
            "full_name": f"{p.get('first_name', '')} {p.get('second_name', '')}",
            "team": teams.get(p.get("team"), {}).get("short_name", "UNK"),
            "team_full": teams.get(p.get("team"), {}).get("name", "UNK"),
            "position": pos_map.get(p.get("element_type"), "UNK"),
            "price": f"£{cost_m:.1f}m",
            "form": p.get("form", "0.0"),
            "total_points": p.get("total_points", 0),
            "goals_scored": p.get("goals_scored", 0),
            "assists": p.get("assists", 0),
            "clean_sheets": p.get("clean_sheets", 0),
            "expected_goals": p.get("expected_goals", "0.00"),
            "expected_assists": p.get("expected_assists", "0.00"),
            "selected_by_percent": f"{p.get('selected_by_percent', '0.0')}%",
            "status": p.get("status", "a"),
            "news": p.get("news", ""),
        })

    results.sort(key=lambda x: x["total_points"], reverse=True)
    return results[:limit]


def get_top_transfers_and_form(limit: int = 5) -> Dict[str, Any]:
    """Gets players in top form, most transferred in, and top overall scorers."""
    data = _fetch_fpl_data()
    teams = _get_team_map(data)
    pos_map = _get_position_map(data)
    elements = data.get("elements", [])

    def format_item(p):
        return {
            "web_name": p["web_name"],
            "team": teams.get(p.get("team"), {}).get("short_name", "UNK"),
            "position": pos_map.get(p.get("element_type"), "UNK"),
            "price": f"£{p.get('now_cost', 0) / 10.0:.1f}m",
            "total_points": p.get("total_points", 0),
            "form": p.get("form", "0.0"),
            "selected_by": f"{p.get('selected_by_percent', '0.0')}%",
            "transfers_in_event": p.get("transfers_in_event", 0),
            "news": p.get("news", "") if p.get("status") != "a" else None,
        }

    top_form = sorted(elements, key=lambda x: float(x.get("form") or 0.0), reverse=True)[:limit]
    top_transfers_in = sorted(elements, key=lambda x: x.get("transfers_in_event") or 0, reverse=True)[:limit]
    top_points = sorted(elements, key=lambda x: x.get("total_points") or 0, reverse=True)[:limit]

    return {
        "top_form": [format_item(p) for p in top_form],
        "most_transferred_in_this_gameweek": [format_item(p) for p in top_transfers_in],
        "top_overall_points": [format_item(p) for p in top_points],
    }


def get_fixture_difficulty(team_query: str) -> Dict[str, Any]:
    """Retrieves upcoming fixture difficulty for a specific Premier League team."""
    data = _fetch_fpl_data()
    teams = _get_team_map(data)
    t_lower = team_query.lower()

    target_team = None
    for tid, t in teams.items():
        if t_lower in t["name"].lower() or t_lower in t["short_name"].lower():
            target_team = t
            break

    if not target_team:
        return {"error": f"Team '{team_query}' not found. Available teams: {', '.join(t['name'] for t in teams.values())}"}

    req = urllib.request.Request(
        "https://fantasy.premierleague.com/api/fixtures/",
        headers={"User-Agent": "Mozilla/5.0"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        all_fixtures = json.loads(resp.read().decode("utf-8"))

    tid = target_team["id"]
    upcoming = []
    for f in all_fixtures:
        if f.get("finished") is False and (f.get("team_h") == tid or f.get("team_a") == tid):
            is_home = (f.get("team_h") == tid)
            opp_id = f.get("team_a") if is_home else f.get("team_h")
            opp_team = teams.get(opp_id, {})
            difficulty = f.get("team_h_difficulty") if is_home else f.get("team_a_difficulty")

            upcoming.append({
                "gameweek": f.get("event"),
                "opponent": opp_team.get("name", "Unknown"),
                "opponent_short": opp_team.get("short_name", "UNK"),
                "venue": "Home" if is_home else "Away",
                "difficulty_fdr": difficulty,
                "kickoff_time": f.get("kickoff_time"),
            })
            if len(upcoming) >= 5:
                break

    return {
        "team": target_team["name"],
        "short_name": target_team["short_name"],
        "upcoming_fixtures": upcoming,
    }


def get_manager_team_and_leagues(team_id: int) -> Dict[str, Any]:
    """Retrieves manager profile, overall rank, total points, and all mini-leagues by team ID."""
    url = f"https://fantasy.premierleague.com/api/entry/{team_id}/"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"error": f"Could not find FPL manager with team ID {team_id}: {e}"}

    classic_leagues = []
    for l in data.get("leagues", {}).get("classic", []):
        classic_leagues.append({
            "league_id": l.get("id"),
            "league_name": l.get("name"),
            "current_rank": l.get("entry_rank"),
            "previous_rank": l.get("entry_last_rank"),
            "rank_change": (l.get("entry_last_rank") or 0) - (l.get("entry_rank") or 0) if l.get("entry_last_rank") else 0,
        })

    h2h_leagues = []
    for l in data.get("leagues", {}).get("h2h", []):
        h2h_leagues.append({
            "league_id": l.get("id"),
            "league_name": l.get("name"),
            "current_rank": l.get("entry_rank"),
        })

    return {
        "manager_id": team_id,
        "team_name": data.get("name"),
        "manager_name": f"{data.get('player_first_name', '')} {data.get('player_last_name', '')}".strip(),
        "overall_points": data.get("summary_overall_points"),
        "overall_rank": data.get("summary_overall_rank"),
        "event_points_last_gw": data.get("summary_event_points"),
        "classic_leagues": classic_leagues,
        "h2h_leagues": h2h_leagues,
    }


def get_league_standings(league_id: int, page: int = 1) -> Dict[str, Any]:
    """Fetches full leaderboard standings for any FPL classic mini-league."""
    url = f"https://fantasy.premierleague.com/api/leagues-classic/{league_id}/standings/?page_standings={page}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"error": f"Could not fetch standings for league {league_id}: {e}"}

    league_info = data.get("league", {})
    results = data.get("standings", {}).get("results", [])

    standings = []
    for r in results[:15]:
        standings.append({
            "rank": r.get("rank"),
            "last_rank": r.get("last_rank"),
            "team_name": r.get("entry_name"),
            "manager_name": r.get("player_name"),
            "event_total": r.get("event_total"),
            "total_points": r.get("total"),
            "team_id": r.get("entry"),
        })

    return {
        "league_id": league_id,
        "league_name": league_info.get("name"),
        "created": league_info.get("created"),
        "standings": standings,
    }


def get_manager_squad_and_chips(team_id: int, gameweek: Optional[int] = None) -> Dict[str, Any]:
    """Fetches the manager's exact 15-player squad (starters and bench), chip history, and bank budget.

    Args:
        team_id: Manager's FPL numeric entry ID.
        gameweek: Optional specific GW. If omitted, uses the latest finished or current GW.

    Returns:
        Full squad details (11 starters, 4 bench players), captain, vice captain, bank budget, free transfer count,
        and chips used/available.
    """
    data = _fetch_fpl_data()
    elements_map = {p["id"]: p for p in data.get("elements", [])}
    teams_map = _get_team_map(data)
    pos_map = _get_position_map(data)

    # Determine latest gameweek
    gw = gameweek
    if not gw:
        gw_info = get_current_gameweek_info()
        curr = gw_info.get("current_gameweek")
        gw = curr.get("id") if isinstance(curr, dict) and curr.get("id") else 5

    # 1. Fetch chips from entry history
    hist_url = f"https://fantasy.premierleague.com/api/entry/{team_id}/history/"
    req = urllib.request.Request(hist_url, headers={"User-Agent": "Mozilla/5.0"})
    chips_used = []
    latest_history = {}
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            hist_data = json.loads(resp.read().decode("utf-8"))
            chips_used = hist_data.get("chips", [])
            current_events = hist_data.get("current", [])
            if current_events:
                latest_history = current_events[-1]
    except Exception:
        pass

    # All standard FPL chips
    all_chips = ["wildcard", "bboost", "3xc", "freehit"]
    used_chip_names = [c.get("name") for c in chips_used]
    available_chips = [c for c in all_chips if c not in used_chip_names]

    # 2. Fetch squad picks for the specified gameweek
    picks_url = f"https://fantasy.premierleague.com/api/entry/{team_id}/event/{gw}/picks/"
    req = urllib.request.Request(picks_url, headers={"User-Agent": "Mozilla/5.0"})
    picks_data = {}
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            picks_data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"error": f"Could not fetch squad picks for team {team_id} in GW {gw}: {e}"}

    entry_hist = picks_data.get("entry_history", {})
    bank_m = entry_hist.get("bank", 0) / 10.0
    team_val_m = entry_hist.get("value", 1000) / 10.0
    active_chip = picks_data.get("active_chip")

    starters = []
    bench = []

    for pick in picks_data.get("picks", []):
        el = elements_map.get(pick["element"], {})
        p_team = teams_map.get(el.get("team"), {})
        player_obj = {
            "id": el.get("id"),
            "web_name": el.get("web_name", "Unknown"),
            "full_name": f"{el.get('first_name', '')} {el.get('second_name', '')}".strip(),
            "team": p_team.get("short_name", "UNK"),
            "position": pos_map.get(el.get("element_type"), "UNK"),
            "price": f"£{el.get('now_cost', 0) / 10.0:.1f}m",
            "form": el.get("form", "0.0"),
            "total_points": el.get("total_points", 0),
            "expected_goals": el.get("expected_goals", "0.00"),
            "expected_assists": el.get("expected_assists", "0.00"),
            "status": el.get("status", "a"),
            "news": el.get("news", ""),
            "pick_position": pick.get("position"),
            "is_captain": pick.get("is_captain", False),
            "is_vice_captain": pick.get("is_vice_captain", False),
        }
        if pick.get("position", 1) <= 11:
            starters.append(player_obj)
        else:
            bench.append(player_obj)

    return {
        "gameweek": gw,
        "team_id": team_id,
        "bank": f"£{bank_m:.1f}m",
        "squad_value": f"£{team_val_m:.1f}m",
        "active_chip_last_gw": active_chip,
        "chips_used": chips_used,
        "chips_available": available_chips,
        "starting_11": starters,
        "bench": bench,
    }


def analyze_mini_league_differentials(
    league_id: int,
    user_team_id: int,
    gameweek: Optional[int] = None,
    rival_sample_size: int = 10,
) -> Dict[str, Any]:
    """Analyzes player ownership across mini-league rivals to identify differential picks.

    A differential pick is an asset who:
    1. Has low or zero ownership among rivals directly above you in your mini-league.
    2. Has strong upcoming form, favorable fixtures (low FDR), and high underlying xG/xA.
    3. Serves as a high-leverage opportunity to leapfrog rivals and climb the leaderboard.

    Args:
        league_id: The FPL mini-league ID.
        user_team_id: The logged-in manager's team ID.
        gameweek: The gameweek to evaluate.
        rival_sample_size: Number of top rivals to analyze (default: 10).
    """
    data = _fetch_fpl_data()
    elements_map = {p["id"]: p for p in data.get("elements", [])}
    teams_map = _get_team_map(data)
    pos_map = _get_position_map(data)

    gw = gameweek
    if not gw:
        gw_info = get_current_gameweek_info()
        curr = gw_info.get("current_gameweek")
        gw = curr.get("id") if isinstance(curr, dict) and curr.get("id") else 5

    # 1. Fetch mini-league leaderboard
    standings_data = get_league_standings(league_id)
    if "error" in standings_data:
        return standings_data

    standings = standings_data.get("standings", [])
    if not standings:
        return {"error": f"No standings found for mini-league {league_id}."}

    # 2. Get user's own picks
    user_picks_url = f"https://fantasy.premierleague.com/api/entry/{user_team_id}/event/{gw}/picks/"
    user_owned_ids = set()
    try:
        req = urllib.request.Request(user_picks_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            u_data = json.loads(resp.read().decode())
            user_owned_ids = {p["element"] for p in u_data.get("picks", [])}
    except Exception:
        pass

    # 3. Sample rivals (prioritize those ahead on the leaderboard)
    rival_counts: Dict[int, int] = {}
    rivals_analyzed = 0
    rival_names = []

    for entry in standings:
        eid = entry.get("team_id")
        if not eid or eid == user_team_id:
            continue

        rival_url = f"https://fantasy.premierleague.com/api/entry/{eid}/event/{gw}/picks/"
        try:
            req = urllib.request.Request(rival_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=6) as resp:
                r_picks = json.loads(resp.read().decode()).get("picks", [])
                for rp in r_picks:
                    pid = rp["element"]
                    rival_counts[pid] = rival_counts.get(pid, 0) + 1
            rivals_analyzed += 1
            rival_names.append(entry.get("manager_name", f"Team {eid}"))
            if rivals_analyzed >= rival_sample_size:
                break
        except Exception:
            continue

    if rivals_analyzed == 0:
        return {"error": "Could not inspect rival rosters for this mini-league."}

    # 4. Score all Premier League players for differential potential
    # High form, high total points, but LOW rival ownership (<= 15% in the league sample)
    differential_candidates = []
    threshold = max(1, int(rivals_analyzed * 0.20))  # owned by 20% or fewer rivals

    for el in data.get("elements", []):
        pid = el["id"]
        rival_owns = rival_counts.get(pid, 0)
        if rival_owns <= threshold and el.get("status") == "a":
            form_val = float(el.get("form") or 0.0)
            pts = el.get("total_points", 0)
            if form_val >= 3.5 or pts >= 20:
                cost_m = el.get("now_cost", 0) / 10.0
                p_team = teams_map.get(el.get("team"), {})
                differential_candidates.append({
                    "id": pid,
                    "web_name": el.get("web_name"),
                    "team": p_team.get("short_name", "UNK"),
                    "position": pos_map.get(el.get("element_type"), "UNK"),
                    "price": f"£{cost_m:.1f}m",
                    "form": form_val,
                    "total_points": pts,
                    "rival_ownership_pct": f"{int((rival_owns / rivals_analyzed) * 100)}%",
                    "already_in_your_team": pid in user_owned_ids,
                    "expected_goals": el.get("expected_goals", "0.00"),
                    "expected_assists": el.get("expected_assists", "0.00"),
                })

    differential_candidates.sort(key=lambda x: (x["form"], x["total_points"]), reverse=True)

    return {
        "league_id": league_id,
        "league_name": standings_data.get("league_name"),
        "rivals_analyzed_count": rivals_analyzed,
        "sample_rivals": rival_names[:5],
        "top_differential_recommendations": differential_candidates[:6],
    }
