"""Aggilli Music Intelligence — catalog-grounded discovery engine.

Deterministic, explainable ranking foundation for future AI DJ. Never returns
tracks without valid commercial interactive-streaming rights. No external AI
API, personal profiling or public playback integration is enabled here.
"""
import math
import re
import unicodedata
from collections import Counter
from datetime import date
from typing import Mapping

from commercial.rights import commercial_catalog

MOODS = {
    "relaxar": {"calm", "ambient", "chill", "relax", "meditation", "instrumental", "new age"},
    "foco": {"instrumental", "ambient", "classical", "focus", "piano", "lofi", "study"},
    "energia": {"dance", "electronic", "rock", "pop", "workout", "energetic", "upbeat"},
    "romantico": {"romantic", "love", "soul", "ballad", "rnb", "jazz"},
    "descoberta": set(),
}
ALIASES = {
    "calma": "relaxar", "tranquilo": "relaxar", "tranquila": "relaxar",
    "meditar": "relaxar", "concentracao": "foco", "estudar": "foco",
    "trabalhar": "foco", "treino": "energia", "animado": "energia",
    "animada": "energia", "amor": "romantico", "surpreenda": "descoberta",
}


def normalize(value: str) -> str:
    if not isinstance(value, str):
        return ""
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def interpret_intent(query: str) -> str:
    """Map common PT-BR listening intents to supported, disclosed mood labels."""
    tokens = set(normalize(query)[:300].split())
    for mood, words in (
        ("foco", {"foco", "concentracao", "estudar", "trabalhar"}),
        ("relaxar", {"relaxar", "calma", "tranquilo", "tranquila", "meditar"}),
        ("energia", {"energia", "treino", "animado", "animada"}),
        ("romantico", {"romantico", "amor", "romance"}),
    ):
        if tokens & words:
            return mood
    return "descoberta"


def recommend(tracks: list[dict], rights_by_id: Mapping, territory: str,
              *, mood: str = "descoberta", limit: int = 10,
              history: list[str] | None = None, today: date | None = None) -> list[dict]:
    """Rank only licensed tracks, without returning raw playback URLs.

    History is a caller-supplied list of IDs, not persisted by this module.
    """
    if mood not in MOODS:
        raise ValueError("Unsupported mood")
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 50:
        raise ValueError("limit must be 1..50")
    if not isinstance(tracks, list) or not isinstance(rights_by_id, Mapping):
        raise ValueError("Invalid catalog")
    allowed = commercial_catalog(tracks, rights_by_id, territory, today)
    recent = set(history[-50:]) if isinstance(history, list) else set()
    seen = set()
    scored = []
    for track in allowed:
        track_id = track["track_id"]
        if track_id in seen:
            continue
        seen.add(track_id)
        media = track.get("media") if isinstance(track.get("media"), dict) else {}
        title = str(media.get("title") or track.get("title") or "")
        artist = str(media.get("artist") or track.get("artist") or "")
        genre = str(media.get("genre") or track.get("genre") or "")
        tags = track.get("tags") if isinstance(track.get("tags"), list) else []
        terms = set(normalize(" ".join([title, artist, genre] + [str(x) for x in tags])).split())
        matched = terms & MOODS[mood]
        score = 2 * len(matched) - (4 if track_id in recent else 0)
        scored.append((score, normalize(artist), track_id, title, artist, sorted(matched)))
    scored.sort(key=lambda row: (-row[0], row[1], row[2]))
    output = []
    artist_counts = Counter()
    remaining = scored[:]
    while remaining and len(output) < limit:
        best = min(range(len(remaining)), key=lambda i: (
            artist_counts[remaining[i][1]], -remaining[i][0], remaining[i][2]
        ))
        score, artist_key, track_id, title, artist, matched = remaining.pop(best)
        artist_counts[artist_key] += 1
        output.append({
            "track_id": track_id, "title": title, "artist": artist,
            "reason": ("Combina com " + mood + ": " + ", ".join(matched))
                      if matched else "Descoberta do catálogo autorizado",
            "mood": mood,
        })
    return output
