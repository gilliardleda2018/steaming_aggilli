# Smart Queue — Aggilli Music Intelligence

`commercial/playback_queue.py` is an immutable state machine for a future
licensed music player. It supports play/pause, next/previous, repeat off/one/all,
deduplication, removing a track and revocation-aware queue reconciliation.

The queue holds **only track IDs**, never raw AzuraCast links. Every playback
request must be independently authorized server-side against the authenticated
listener, active subscription, current territorial rights and the requested
track. A prior recommendation or queue inclusion is **not** playback permission.

The engine does not yet stream audio, store listening history, manage Android
MediaSession or modify the public Winamp. Integrate it with a separate
authorized media gateway in staging after licenses and payment enforcement
are validated. Revocation must also terminate any active stream; a UI-only
queue refresh is insufficient.

Tests cover navigation, repeat, empty queues, duplicate IDs and rights
revocation while playing.
