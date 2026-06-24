"""
models.py — Data model factories and save-file migration.

All campaign data is plain dicts so it serialises cleanly to JSON.
When the save format changes, bump SAVE_VERSION and add a migration step
in migrate() — old saves are upgraded automatically on load.
"""

from __future__ import annotations
from datetime import datetime

SAVE_VERSION = 1  # increment when the schema changes


def _id() -> str:
    return datetime.now().strftime("%Y%m%d%H%M%S%f")


def new_map_entry(name: str = "New Map", path: str = "",
                  pixels_per_unit: float | None = None,
                  unit_name: str = "miles") -> dict:
    return {
        "id":              _id(),
        "name":            name,
        "path":            path,
        "pixels_per_unit": pixels_per_unit,
        "unit_name":       unit_name,
        "measurements":    [],
    }


# ── Constructors ──────────────────────────────────────────────────────────────

def new_campaign(name: str = "Unnamed Campaign") -> dict:
    return {
        "save_version": SAVE_VERSION,
        "meta": {
            "name": name,
            "created": datetime.now().isoformat(),
            "modified": datetime.now().isoformat(),
            "dm": "", "setting": "", "notes": "",
        },
        "sessions": [],
        "characters": [],
        "lore": [],
        "locations": [],
        "maps": [],
        "graph_annotations": [],
        "graph_positions": {},
    }


def new_session(name: str = "") -> dict:
    return {
        "id": _id(),
        "name": name or f"Session {datetime.now().strftime('%Y-%m-%d')}",
        "date": datetime.now().strftime("%Y-%m-%d"),
        "summary": "", "notes": "",
        "linked": [],
        "created": datetime.now().isoformat(),
    }


def new_character(name: str = "") -> dict:
    return {
        "id": _id(), "name": name or "Unknown",
        "role": "NPC", "race": "", "class_or_job": "",
        "location_id": "", "status": "Alive",
        "first_seen": "", "notes": "",
        "linked": [],
        "created": datetime.now().isoformat(),
    }


def new_lore(title: str = "") -> dict:
    return {
        "id": _id(),
        "title": title or "Untitled Entry",
        "category": "World",
        "content": "",
        "linked": [],
        "created": datetime.now().isoformat(),
    }


def new_location(name: str = "", parent_id: str = "") -> dict:
    return {
        "id": _id(), "name": name or "Unknown Place",
        "parent_id": parent_id,
        "type": "City",
        "faction": "", "status": "Unknown",
        "notes": "", "secrets": "", "loot": "",
        "linked": [],
        "created": datetime.now().isoformat(),
    }


# ── Migration ─────────────────────────────────────────────────────────────────

def migrate(data: dict) -> dict:
    """
    Upgrade a loaded campaign dict to the current SAVE_VERSION in-place.
    Add a new elif block here whenever SAVE_VERSION bumps.
    """
    version = data.get("save_version", 0)

    if version == SAVE_VERSION:
        return data  # already current

    # v0 → v1: add all fields introduced in the initial structured release
    if version < 1:
        data.setdefault("save_version", 1)
        data.setdefault("graph_annotations", [])
        data.setdefault("graph_positions", {})
        data.setdefault("locations", [])
        data.setdefault("maps", [])
        meta = data.setdefault("meta", {})
        meta.setdefault("dm", "")
        meta.setdefault("setting", "")
        meta.setdefault("notes", "")

        # Migrate old single map_path / map_data into the maps list
        old_path = meta.pop("map_path", "")
        old_data = meta.pop("map_data", {})
        if old_path and not data["maps"]:
            data["maps"].append(new_map_entry(
                name="Map",
                path=old_path,
                pixels_per_unit=old_data.get("calibration", {}).get("pixels_per_unit"),
                unit_name=old_data.get("calibration", {}).get("unit_name", "miles"),
            ))
            # Migrate old measurements into the new map entry
            if old_data.get("measurements"):
                data["maps"][0]["measurements"] = old_data["measurements"]

        for key in ("sessions", "characters", "lore", "locations"):
            for item in data.get(key, []):
                item.setdefault("linked", [])

    # Future: elif version < 2: ...

    data["save_version"] = SAVE_VERSION
    return data