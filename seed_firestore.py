# Copyright 2026 Google LLC
# Firestore seed script for FPL Scout watchlist and team profile

from datetime import datetime, timezone
from google.cloud import firestore

PROJECT_ID = "qwiklabs-gcp-04-2d53b9c1010c"
COLLECTION_NAME = "fpl_watchlist"

SEED_TARGETS = [
    {
        "id": "erling_haaland",
        "player_id": 411,
        "web_name": "Haaland",
        "full_name": "Erling Haaland",
        "team": "MCI",
        "position": "FWD",
        "price_bought": 15.2,
        "target_price": 15.6,
        "priority": "essential",
        "notes": "Primary perma-captain candidate. On penalties and explosive xG form.",
        "added_at": datetime.now(timezone.utc).isoformat(),
    },
    {
        "id": "bryan_mbeumo",
        "player_id": 98,
        "web_name": "Mbeumo",
        "full_name": "Bryan Mbeumo",
        "team": "BRE",
        "position": "MID",
        "price_bought": 7.1,
        "target_price": 7.3,
        "priority": "high",
        "notes": "Talisman for Brentford, high xG, takes penalties and corners.",
        "added_at": datetime.now(timezone.utc).isoformat(),
    },
    {
        "id": "antoine_semenyo",
        "player_id": 65,
        "web_name": "Semenyo",
        "full_name": "Antoine Semenyo",
        "team": "BOU",
        "position": "MID",
        "price_bought": 5.6,
        "target_price": 5.7,
        "priority": "medium",
        "notes": "High shot volume budget enabler for Bournemouth attack.",
        "added_at": datetime.now(timezone.utc).isoformat(),
    },
    {
        "id": "gabriel_magalhaes",
        "player_id": 19,
        "web_name": "Gabriel",
        "full_name": "Gabriel dos Santos Magalhães",
        "team": "ARS",
        "position": "DEF",
        "price_bought": 6.0,
        "target_price": 6.2,
        "priority": "high",
        "notes": "Best set-piece aerial goal threat defender in the league.",
        "added_at": datetime.now(timezone.utc).isoformat(),
    },
]


def seed_database():
    print(f"Connecting to Firestore with hardcoded project ID: '{PROJECT_ID}'...")
    db = firestore.Client(project=PROJECT_ID)
    collection = db.collection(COLLECTION_NAME)

    for item in SEED_TARGETS:
        doc_id = item["id"]
        doc_ref = collection.document(doc_id)
        doc_ref.set(item)
        print(f"  ✓ Seeded {item['web_name']} ({item['team']} - {item['position']}) -> {doc_id}")

    print(f"\nSuccessfully seeded {len(SEED_TARGETS)} players into '{COLLECTION_NAME}'!")


if __name__ == "__main__":
    seed_database()
