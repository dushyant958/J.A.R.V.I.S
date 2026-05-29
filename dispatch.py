"""
Dispatch J.A.R.V.I.S to a room.

Usage:
    python dispatch.py              # dispatches to default room "jarvis-room"
    python dispatch.py my-room      # dispatches to a specific room
"""

import asyncio
import sys
from dotenv import load_dotenv
from livekit import api

load_dotenv()

AGENT_NAME = "jarvis"
DEFAULT_ROOM = "jarvis-room"


async def dispatch(room_name: str):
    lkapi = api.LiveKitAPI()
    d = await lkapi.agent_dispatch.create_dispatch(
        api.CreateAgentDispatchRequest(agent_name=AGENT_NAME, room=room_name)
    )
    print(f"Dispatched '{d.agent_name}' to room '{d.room}'")
    await lkapi.aclose()


if __name__ == "__main__":
    room = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_ROOM
    asyncio.run(dispatch(room))
