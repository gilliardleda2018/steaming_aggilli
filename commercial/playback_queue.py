"""Aggilli Music Intelligence — pure playback queue state machine.

A session manages IDs only. No raw streaming URLs, audio decoding, billing
or production player changes. The authorized playback gateway is separate.
"""
from dataclasses import dataclass, replace


@dataclass(frozen=True)
class QueueState:
    track_ids: tuple[str, ...] = ()
    index: int = -1
    playing: bool = False
    repeat: str = "off"  # off, one, all

    @property
    def current(self) -> str | None:
        if 0 <= self.index < len(self.track_ids):
            return self.track_ids[self.index]
        return None


def create_queue(ids: list[str], *, max_tracks: int = 100) -> QueueState:
    if not isinstance(ids, list) or len(ids) > max_tracks:
        raise ValueError("Invalid queue")
    if any(not isinstance(x, str) or not x or len(x) > 128 for x in ids):
        raise ValueError("Invalid track ID")
    unique = tuple(dict.fromkeys(ids))
    return QueueState(unique, 0 if unique else -1)


def play(state: QueueState) -> QueueState:
    return replace(state, playing=bool(state.current))


def pause(state: QueueState) -> QueueState:
    return replace(state, playing=False)


def next_track(state: QueueState) -> QueueState:
    if not state.track_ids:
        return pause(state)
    if state.repeat == "one" and state.playing:
        return state
    if state.index + 1 < len(state.track_ids):
        return replace(state, index=state.index + 1)
    if state.repeat == "all":
        return replace(state, index=0)
    return replace(state, playing=False)


def previous_track(state: QueueState) -> QueueState:
    if not state.track_ids:
        return pause(state)
    if state.index > 0:
        return replace(state, index=state.index - 1)
    if state.repeat == "all":
        return replace(state, index=len(state.track_ids) - 1)
    return state


def set_repeat(state: QueueState, mode: str) -> QueueState:
    if mode not in {"off", "one", "all"}:
        raise ValueError("Invalid repeat mode")
    return replace(state, repeat=mode)


def remove_track(state: QueueState, track_id: str) -> QueueState:
    if track_id not in state.track_ids:
        return state
    pos = state.track_ids.index(track_id)
    ids = state.track_ids[:pos] + state.track_ids[pos + 1:]
    if not ids:
        return QueueState(repeat=state.repeat)
    if pos < state.index:
        index = state.index - 1
    elif pos == state.index:
        index = min(pos, len(ids) - 1)
    else:
        index = state.index
    return QueueState(ids, index, state.playing, state.repeat)


def reconcile_eligible(state: QueueState, eligible_ids: set[str]) -> QueueState:
    """Remove revoked/expired tracks; stop playback if current loses rights."""
    if not isinstance(eligible_ids, set):
        raise ValueError("Invalid eligibility set")
    current = state.current
    ids = tuple(x for x in state.track_ids if x in eligible_ids)
    if not ids:
        return QueueState(repeat=state.repeat)
    if current in ids:
        index = ids.index(current)
        playing = state.playing
    else:
        index = min(sum(x in eligible_ids for x in state.track_ids[:max(state.index, 0)]), len(ids) - 1)
        playing = False
    return QueueState(ids, index, playing, state.repeat)
