"""Mint LiveKit Cloud access tokens so each interview participant can join the room.

The media (camera/mic) flows through LiveKit's hosted SFU/TURN, so it connects across
different networks without exposing anyone's IP. The backend only signs a short-lived
join token with the LiveKit API key/secret; it never relays media itself.
"""

import os
from datetime import timedelta

from livekit import api


def _get(name: str) -> str:
    return os.getenv(name, "").strip()


def is_configured() -> bool:
    return bool(_get("LIVEKIT_URL") and _get("LIVEKIT_API_KEY") and _get("LIVEKIT_API_SECRET"))


def livekit_url() -> str:
    return _get("LIVEKIT_URL")


def mint_token(*, identity: str, name: str, room: str, ttl_minutes: int = 180) -> str:
    """Create a join token that lets `identity` publish and subscribe in `room`."""
    return (
        api.AccessToken(_get("LIVEKIT_API_KEY"), _get("LIVEKIT_API_SECRET"))
        .with_identity(identity)
        .with_name(name)
        .with_ttl(timedelta(minutes=ttl_minutes))
        .with_grants(api.VideoGrants(
            room_join=True,
            room=room,
            can_publish=True,
            can_subscribe=True,
        ))
        .to_jwt()
    )
