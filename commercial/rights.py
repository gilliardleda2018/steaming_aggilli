"""Isolated commercial music rights registry. Not wired into production playback.

Fail-closed: only tracks with explicit active, unexpired on-demand streaming
rights in the requested territory may be offered by a future commercial API.
No assumption that a file in AzuraCast/Nextcloud is licensed.
"""
from datetime import date
from typing import Mapping


def eligible_for_streaming(record: Mapping, territory: str, today: date | None = None) -> bool:
    if today is None:
        today = date.today()
    if not isinstance(record, Mapping) or not isinstance(territory, str):
        return False
    if record.get("status") != "approved":
        return False
    if record.get("license_type") != "interactive_streaming":
        return False
    if not record.get("agreement_reference") or not record.get("rights_holder"):
        return False
    if not record.get("recording_rights_confirmed") or not record.get("composition_rights_confirmed"):
        return False
    territories = record.get("territories")
    if not isinstance(territories, list) or territory.upper() not in territories:
        return False
    try:
        start = date.fromisoformat(record["valid_from"])
        end = date.fromisoformat(record["valid_until"])
    except (KeyError, TypeError, ValueError):
        return False
    return start <= today <= end


def commercial_catalog(tracks: list[dict], rights_by_id: Mapping, territory: str, today: date | None = None) -> list[dict]:
    """Return only approved tracks; never mutate the existing catalog."""
    return [
        track for track in tracks
        if isinstance(track, dict)
        and isinstance(track.get("track_id"), str)
        and eligible_for_streaming(rights_by_id.get(track["track_id"]), territory, today)
    ]
