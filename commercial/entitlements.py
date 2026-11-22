"""Fail-closed commercial playback entitlement policy (no production wiring).

All inputs must come from trusted server-side records, never from a client
claim. This module does not serve media or validate identity tokens.
"""
from datetime import date, datetime, timezone
from typing import Mapping

from commercial.rights import eligible_for_streaming


def allowed_to_play(
    listener: Mapping | None,
    subscription: Mapping | None,
    rights: Mapping | None,
    territory: str,
    *,
    now: datetime | None = None,
) -> bool:
    """Require active account, active paid entitlement and valid track rights."""
    if now is None:
        now = datetime.now(timezone.utc)
    if now.tzinfo is None:
        return False
    now = now.astimezone(timezone.utc)
    if not all(isinstance(x, Mapping) for x in (listener, subscription, rights)):
        return False
    if listener.get("status") != "active" or not listener.get("id"):
        return False
    if subscription.get("listener_id") != listener.get("id"):
        return False
    if subscription.get("status") not in {"active", "trialing"}:
        return False
    if subscription.get("plan") not in {"premium", "family"}:
        return False
    if not isinstance(territory, str) or len(territory) != 2 or not territory.isalpha():
        return False
    expires = subscription.get("access_until")
    if not isinstance(expires, str):
        return False
    try:
        expiry = datetime.fromisoformat(expires.replace("Z", "+00:00"))
    except ValueError:
        return False
    if expiry.tzinfo is None or expiry.astimezone(timezone.utc) <= now:
        return False
    return eligible_for_streaming(rights, territory.upper(), now.date())
