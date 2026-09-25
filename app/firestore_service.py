# Copyright 2026 Google LLC
# Firestore repository service for FPL Watchlist, User Team Profile, and Gameweek Plans
# Note: PROJECT_ID is hardcoded as required for Agent Runtime compatibility.

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from google.cloud import firestore

PROJECT_ID = "qwiklabs-gcp-04-2d53b9c1010c"
COLLECTION_WATCHLIST = "fpl_watchlist"
COLLECTION_USER_PROFILE = "fpl_user_profile"
DEFAULT_USER_KEY = "current_user"

_db_client: Optional[firestore.Client] = None


def get_firestore_client() -> firestore.Client:
    global _db_client
    if _db_client is None:
        _db_client = firestore.Client(project=PROJECT_ID)
    return _db_client


# ==================== USER PROFILE & TEAM STORAGE ====================


def save_user_profile(
    team_id: int,
    user_name: Optional[str] = None,
    fpl_team_name: Optional[str] = None,
    favorite_club: Optional[str] = None,
    auto_sync_leagues: bool = True,
    leagues_data: Optional[List[Dict[str, Any]]] = None,
    squad_summary: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Stores the logged-in user's FPL Team ID, manager profile, and mini-leagues into Firestore."""
    db = get_firestore_client()
    col = db.collection(COLLECTION_USER_PROFILE)

    payload: Dict[str, Any] = {
        "team_id": int(team_id),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if user_name:
        payload["user_name"] = user_name
    if fpl_team_name:
        payload["fpl_team_name"] = fpl_team_name
    if favorite_club:
        payload["favorite_club"] = favorite_club
    if leagues_data is not None:
        payload["leagues"] = leagues_data
    if squad_summary is not None:
        payload["squad_summary"] = squad_summary

    doc_ref = col.document(DEFAULT_USER_KEY)
    doc_ref.set(payload, merge=True)
    return {"status": "success", "user_key": DEFAULT_USER_KEY, "profile": payload}


def get_user_profile() -> Optional[Dict[str, Any]]:
    """Retrieves the stored logged-in user's profile and FPL Team ID from Firestore."""
    db = get_firestore_client()
    doc_ref = db.collection(COLLECTION_USER_PROFILE).document(DEFAULT_USER_KEY)
    snap = doc_ref.get()
    if snap.exists:
        return snap.to_dict()
    return None


# ==================== WATCHLIST ====================


def list_watchlist_items(priority: Optional[str] = None) -> List[Dict[str, Any]]:
    """Reads all players stored in the user's FPL transfer watchlist from Firestore."""
    db = get_firestore_client()
    col = db.collection(COLLECTION_WATCHLIST)

    docs = col.stream()
    items = []
    for doc in docs:
        d = doc.to_dict()
        if priority and d.get("priority", "").lower() != priority.lower():
            continue
        items.append(d)

    priority_weights = {"essential": 1, "high": 2, "medium": 3, "low": 4}
    items.sort(key=lambda x: priority_weights.get(x.get("priority", "medium").lower(), 99))
    return items


def add_or_update_watchlist_item(
    web_name: str,
    team: str,
    position: str,
    target_price: float,
    priority: str = "medium",
    notes: str = "",
) -> Dict[str, Any]:
    """Adds a new player or updates an existing player in the user's FPL watchlist in Firestore."""
    db = get_firestore_client()
    col = db.collection(COLLECTION_WATCHLIST)

    doc_id = re.sub(r"[^a-zA-Z0-9_]+", "_", f"{web_name}_{team}".lower())
    payload = {
        "id": doc_id,
        "web_name": web_name.strip(),
        "team": team.strip().upper(),
        "position": position.strip().upper(),
        "target_price": float(target_price),
        "priority": priority.strip().lower(),
        "notes": notes.strip(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    doc_ref = col.document(doc_id)
    doc_ref.set(payload, merge=True)
    return {"status": "success", "doc_id": doc_id, "player": payload}


def remove_from_watchlist(web_name: str, team: Optional[str] = None) -> Dict[str, Any]:
    """Removes a player from the FPL watchlist in Firestore."""
    db = get_firestore_client()
    col = db.collection(COLLECTION_WATCHLIST)

    q = web_name.strip().lower()
    docs = col.stream()
    deleted = []
    for doc in docs:
        data = doc.to_dict()
        name_match = (data.get("web_name", "").lower() == q or q in data.get("id", ""))
        team_match = True
        if team:
            team_match = (data.get("team", "").lower() == team.strip().lower())

        if name_match and team_match:
            doc.reference.delete()
            deleted.append(data.get("web_name"))

    if deleted:
        return {"status": "success", "deleted": deleted}
    return {"status": "not_found", "message": f"No player matching '{web_name}' found in watchlist."}
