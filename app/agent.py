# Copyright 2026 Google LLC
# Licensed under the Apache License, Version 2.0 (the "License");

import os
from typing import Any, Dict, List, Optional
from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.manager import A2uiSchemaManager
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.memory import VertexAiMemoryBankService
from google.adk.models import Gemini
from google.adk.tools import ToolContext
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.genai import types

from app.a2ui_utils import a2ui_callback
from app.fpl_service import (
    get_current_gameweek_info,
    search_players,
    get_top_transfers_and_form,
    get_fixture_difficulty,
    get_manager_team_and_leagues,
    get_league_standings,
    get_manager_squad_and_chips,
    analyze_mini_league_differentials,
)
from app.firestore_service import (
    save_user_profile,
    get_user_profile,
    list_watchlist_items,
    add_or_update_watchlist_item,
    remove_from_watchlist,
)
from app.image_service import generate_and_upload_image

MODEL = "gemini-3.6-flash"
PROJECT_ID = "qwiklabs-gcp-04-2d53b9c1010c"
LOCATION = "us-east1"
MEMORY_BANK_ID = "807048131857350656"


# ==================== MEMORY BANK SERVICE CONFIGURATION ====================


def memory_bank_service_builder() -> VertexAiMemoryBankService:
    """Creates the managed Vertex AI Memory Bank service reusing our deployed Agent Engine."""
    return VertexAiMemoryBankService(
        project=PROJECT_ID,
        location=LOCATION,
        agent_engine_id=MEMORY_BANK_ID,
    )


async def generate_memories_callback(callback_context: CallbackContext) -> None:
    """WRITE callback: Extracts durable user preferences, tactical rules, and facts across conversations."""
    try:
        await callback_context.add_session_to_memory()
    except Exception:
        pass
    return None


# ==================== IMAGE GENERATION & VISUAL DOMAIN TOOLS ====================


async def generate_fpl_visual(
    prompt: str,
    visual_type: str = "formation_pitch",
    tool_context: Optional[ToolContext] = None,
) -> Dict[str, Any]:
    """Generates an image for the FPL domain (formation pitches, graphics) using gemini-3.1-flash-lite-image in the global region."""
    image_bytes, mime_type, filename, public_url = generate_and_upload_image(
        prompt=prompt,
        filename_prefix=visual_type,
    )

    if tool_context:
        try:
            artifact_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
            await tool_context.save_artifact(filename=filename, artifact=artifact_part)
        except Exception:
            pass

    return {
        "status": "success",
        "image_url": public_url,
        "filename": filename,
        "message": f"Image generated and uploaded to public bucket. Public URL: {public_url}",
    }


async def generate_chip_activation_banner(
    chip_name: str,
    gameweek: int,
    manager_or_team_name: str = "My FPL Team",
    rationale: str = "Maximum points optimization",
    tool_context: Optional[ToolContext] = None,
) -> Dict[str, Any]:
    """Generates a high-energy broadcast celebration banner image when an FPL chip is activated."""
    chip_clean = chip_name.title()
    prompt = (
        f"A dramatic, cinematic Premier League sports broadcast graphic banner announcing the activation of the '{chip_clean}' chip for Gameweek {gameweek}. "
        f"Featuring dynamic gold and purple glowing lighting, football stadium floodlights, lens flare, typography reading '{chip_clean.upper()} ACTIVATED - GAMEWEEK {gameweek}', "
        f"team banner for '{manager_or_team_name}', tactical strategy headline '{rationale}', bold esports broadcast visual styling."
    )
    return await generate_fpl_visual(
        prompt=prompt,
        visual_type=f"chip_{chip_name.lower().replace(' ', '_')}",
        tool_context=tool_context,
    )


async def generate_player_scout_card(
    player_name: str,
    team: Optional[str] = None,
    tool_context: Optional[ToolContext] = None,
) -> Dict[str, Any]:
    """Generates an Ultimate Team / FIFA style player radar & scouting card image for any Premier League player."""
    stats_list = search_players(query=player_name, limit=1)
    if stats_list:
        p = stats_list[0]
        prompt = (
            f"An ultra-premium FIFA Ultimate Team style glowing card for Premier League football star {p['full_name']} playing for {p['team_full']} ({p['team']}). "
            f"Position: {p['position']}. FPL Price: {p['price']}. Current Form: {p['form']}. Total Points: {p['total_points']}. "
            f"Card displays a sleek modern radar chart polygon showing Pace, Shooting (xG {p['expected_goals']}), Playmaking (xA {p['expected_assists']}), "
            f"Defending, and Fixture Rating. Gold border, neon accents, Premier League official style badge, high resolution sports card design."
        )
    else:
        prompt = (
            f"An ultra-premium Ultimate Team style glowing football player card for Premier League player {player_name}. "
            f"Featuring holographic gold accents, radar chart graphic polygon, player stats rating, and bold typography on a dark modern background."
        )

    return await generate_fpl_visual(
        prompt=prompt,
        visual_type=f"scout_card_{player_name.lower().replace(' ', '_')}",
        tool_context=tool_context,
    )


# ==================== MINI-LEAGUE DIFFERENTIAL ANALYSIS ====================


def recommend_gameweek_differentials(
    league_id: Optional[int] = None,
    team_id: Optional[int] = None,
    gameweek: Optional[int] = None,
) -> Dict[str, Any]:
    """Analyzes player ownership across your mini-league rivals to identify high-upside differential picks.

    A differential pick is a player owned by very few rivals in your mini-league (under 20% ownership) but with
    high form, strong underlying xG/xA stats, and favorable fixtures to help you leapfrog rivals and climb the leaderboard.
    """
    effective_team = team_id
    effective_league = league_id

    if not effective_team or not effective_league:
        user_profile = get_user_profile()
        if user_profile:
            effective_team = effective_team or user_profile.get("team_id")
            if not effective_league:
                leagues = user_profile.get("leagues", [])
                if leagues:
                    effective_league = leagues[0].get("league_id")

    if not effective_team:
        return {"error": "Please provide your team_id or link your team using register_user_fpl_team."}
    if not effective_league:
        return {"error": "No mini-league ID found. Please specify league_id or register your team to auto-sync leagues."}

    return analyze_mini_league_differentials(
        league_id=effective_league,
        user_team_id=effective_team,
        gameweek=gameweek,
    )


# ==================== USER IDENTITY & PREFERENCES ====================


def register_user_fpl_team(
    team_id: int,
    user_name: Optional[str] = None,
    favorite_club: Optional[str] = None,
) -> Dict[str, Any]:
    """Saves the logged-in user's FPL Team ID, manager profile, and mini-leagues into persistent Firestore storage."""
    profile = get_manager_team_and_leagues(team_id=team_id)
    if "error" in profile:
        return profile

    save_user_profile(
        team_id=team_id,
        user_name=user_name or profile.get("manager_name"),
        fpl_team_name=profile.get("team_name"),
        favorite_club=favorite_club,
        leagues_data=profile.get("classic_leagues", []),
    )
    return {
        "status": "success",
        "message": f"Successfully linked FPL Team ID {team_id} ({profile.get('team_name')}) to your profile!",
        "manager_name": profile.get("manager_name"),
        "overall_rank": profile.get("overall_rank"),
        "total_points": profile.get("overall_points"),
        "leagues_count": len(profile.get("classic_leagues", [])),
    }


def get_current_user_fpl_profile() -> Dict[str, Any]:
    """Retrieves the currently linked user's stored FPL profile and team ID from Firestore."""
    user_doc = get_user_profile()
    if not user_doc:
        return {"status": "unregistered", "message": "No FPL Team ID is currently linked. Please register with register_user_fpl_team(team_id)."}
    return user_doc


# ==================== SQUAD, BENCH, TRANSFERS & CHIPS ====================


def get_squad_lineup_and_chips(team_id: Optional[int] = None, gameweek: Optional[int] = None) -> Dict[str, Any]:
    """Fetches the user's complete 15-man squad (11 starters + 4 bench), bank budget, and chip statuses."""
    effective_id = team_id
    if not effective_id:
        user_profile = get_user_profile()
        if user_profile and "team_id" in user_profile:
            effective_id = user_profile["team_id"]
        else:
            return {"error": "No team ID provided and no registered user team found. Please provide team_id or register with register_user_fpl_team."}

    return get_manager_squad_and_chips(team_id=effective_id, gameweek=gameweek)


def evaluate_transfer_hit(
    player_out: str,
    player_in: str,
    points_cost: int = 4,
) -> Dict[str, Any]:
    """Analyzes whether it is mathematically worth taking a negative point hit (-4 or -8) to make an extra transfer."""
    p_out = search_players(player_out, limit=1)
    p_in = search_players(player_in, limit=1)

    return {
        "transfer_hit_cost": f"-{points_cost} points",
        "selling": p_out[0] if p_out else f"Player '{player_out}' not found",
        "buying": p_in[0] if p_in else f"Player '{player_in}' not found",
        "evaluation_rule": (
            "A -4 hit is worth taking if: "
            "(1) The player out is injured/suspended with 0 expected minutes, OR "
            "(2) The incoming player has an explosive fixture/captaincy upside expected to outscore the outgoing player by at least 4-6 points over the next 2-3 gameweeks."
        ),
    }


# ==================== GENERAL LIVE FPL & WATCHLIST TOOLS ====================


def check_gameweek_status() -> Dict[str, Any]:
    """Retrieves live Fantasy Premier League gameweek status, deadlines, and averages."""
    return get_current_gameweek_info()


def get_player_stats(
    query: str,
    position: Optional[str] = None,
    max_price: Optional[float] = None,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """Searches and compares Premier League players for FPL stats, form, price, and underlying xG/xA metrics."""
    return search_players(query=query, position=position, max_price=max_price, limit=limit)


def get_scouting_recommendations(limit: int = 5) -> Dict[str, Any]:
    """Retrieves top trending FPL assets: players in peak form, most transferred in this GW, and top scorers."""
    return get_top_transfers_and_form(limit=limit)


def check_team_fixtures(team_name: str) -> Dict[str, Any]:
    """Fetches upcoming fixtures and Fixture Difficulty Rating (FDR 1=easy to 5=hard) for a team."""
    return get_fixture_difficulty(team_query=team_name)


def get_my_team_and_leagues(team_id: Optional[int] = None) -> Dict[str, Any]:
    """Retrieves manager profile, overall rank, total points, and all mini-leagues (classic & H2H)."""
    effective_id = team_id
    if not effective_id:
        user_profile = get_user_profile()
        if user_profile and "team_id" in user_profile:
            effective_id = user_profile["team_id"]
        else:
            return {"error": "Please provide a team_id or link your team using register_user_fpl_team."}
    return get_manager_team_and_leagues(team_id=effective_id)


def get_mini_league_standings(league_id: int, page: int = 1) -> Dict[str, Any]:
    """Fetches leaderboard standings for any classic mini-league by League ID."""
    return get_league_standings(league_id=league_id, page=page)


def get_saved_watchlist(priority: Optional[str] = None) -> List[Dict[str, Any]]:
    """Reads the manager's saved transfer targets and watchlist from the Firestore database."""
    return list_watchlist_items(priority=priority)


def save_player_to_watchlist(
    web_name: str,
    team: str,
    position: str,
    target_price: float,
    priority: str = "medium",
    notes: str = "",
) -> Dict[str, Any]:
    """Saves or updates an FPL player in the manager's persistent Firestore watchlist."""
    return add_or_update_watchlist_item(
        web_name=web_name,
        team=team,
        position=position,
        target_price=target_price,
        priority=priority,
        notes=notes,
    )


def remove_player_from_watchlist(web_name: str, team: Optional[str] = None) -> Dict[str, Any]:
    """Deletes a player from the persistent Firestore watchlist."""
    return remove_from_watchlist(web_name=web_name, team=team)


def recommend_captain(candidate_1: str, candidate_2: str) -> str:
    """Compares two captain candidates by looking up their recent form, points, and next fixtures."""
    p1 = search_players(candidate_1, limit=1)
    p2 = search_players(candidate_2, limit=1)
    return f"Candidate 1 stats: {p1}. Candidate 2 stats: {p2}. Analyze their form, xG/xA, and upcoming fixture to recommend the best captain pick."


# ==================== A2UI SCHEMA & SYSTEM PROMPT ====================

schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

instruction = schema_manager.generate_system_prompt(
    role_description=(
        "You are 'The FPL Scout', an expert, data-driven Fantasy Premier League (fantasy.premierleague.com) companion.\n"
        "You remember the user's stated team choices, chip strategies, and managerial preferences across conversations.\n"
        "Your mission is to provide personalized, high-IQ tactical advice for the user:\n"
        "1. MINI-LEAGUE DIFFERENTIALS & LEADERBOARD CLIMBING (recommend_gameweek_differentials)\n"
        "2. WEEKLY STARTING 11, BENCH ORDER & FORMATION (get_squad_lineup_and_chips)\n"
        "3. TRANSFER HITS EVALUATION (evaluate_transfer_hit)\n"
        "4. CHIP STRATEGIES & ACTIVATION BANNERS (generate_chip_activation_banner)\n"
        "5. PLAYER SCOUT CARDS & TACTICAL VISUALS (generate_player_scout_card, generate_fpl_visual)\n"
        "6. PERSISTENT WATCHLIST & USER PROFILE (register_user_fpl_team, get_saved_watchlist, save_player_to_watchlist)"
    ),
    workflow_description="Analyze the user request, call the relevant scouting and tactical tools, and return structured A2UI display cards and tables when appropriate.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, Divider, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        "{\"Image\": {\"url\": {\"literalString\": \"https://storage.googleapis.com/...\"}}}. Never point an "
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model=MODEL,
        client_kwargs={"location": "global"},
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=instruction,
    tools=[
        PreloadMemoryTool(),
        recommend_gameweek_differentials,
        generate_chip_activation_banner,
        generate_player_scout_card,
        generate_fpl_visual,
        register_user_fpl_team,
        get_current_user_fpl_profile,
        get_squad_lineup_and_chips,
        evaluate_transfer_hit,
        get_saved_watchlist,
        save_player_to_watchlist,
        remove_player_from_watchlist,
        get_my_team_and_leagues,
        get_mini_league_standings,
        check_gameweek_status,
        get_player_stats,
        get_scouting_recommendations,
        check_team_fixtures,
        recommend_captain,
    ],
    after_model_callback=a2ui_callback,
    after_agent_callback=generate_memories_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
