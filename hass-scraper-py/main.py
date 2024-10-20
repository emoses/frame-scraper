import asyncio
import logging
import sys
import os
import re
from contextlib import suppress

from dotenv import load_dotenv

from aiohttp import ClientSession

from hass_client import HomeAssistantClient
from hass_client.models import Event

LOGGER = logging.getLogger()

async def start() -> None:
    """Run main."""

    load_dotenv()

    token = os.getenv("HASS_TOKEN")
    if not token:
        LOGGER.error("Missing env var HASS_TOKEN")
        sys.exit(1)


    url = os.getenv("HASS_URL")
    if not url:
        LOGGER.error("Missing env var HASS_URL")
        sys.exit(1)
    url = re.sub("^http", "ws", url)
    if not url.startswith("ws"):
        url = f'ws://{url}'

    logging.basicConfig(level=logging.DEBUG)

    async with ClientSession() as session:
        await connect(token, url, session)


async def connect(token: str, url: str, session: ClientSession) -> None:
    """Connect to the server."""
    websocket_url =  f"{url}/api/websocket"
    async with HomeAssistantClient(websocket_url, token, session) as client:
        await client.subscribe_entities(art_mode_toggle, ["input_boolean.tv_art_mode"])
        await asyncio.sleep(300)

def art_mode_toggle(event: Event) -> None:
    LOGGER.info("Received event %s", event)


def main() -> None:
    asyncio.run(start())


if __name__ == "__main__":
    main()
