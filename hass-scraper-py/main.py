import asyncio
import logging
import sys
import os
import re

from dotenv import load_dotenv
from functools import partial
from aiohttp import ClientSession

from hass_client import HomeAssistantClient
from hass_client.exceptions import ConnectionFailed
from hass_client.models import EntityStateEvent

import scraper

LOGGER = logging.getLogger()

artMode = False


async def hassLoop(token: str, url: str) -> None:
    while True:
        try:
            async with ClientSession() as session:
                listener = await connect(token, url, session)
                LOGGER.debug("connected")
                await listener
                LOGGER.info("Connect complete")
        except ConnectionFailed as e:
            LOGGER.error("Connection error, reconnecting", e)
            await asyncio.sleep(60)

async def scrapeLoop() -> None:
    while True:
        if artMode == False:
            screenshot = await scrape()
            with open('/output/latest.png', 'wb') as f:
                f.write(screenshot)
        else:
            LOGGER.debug("art mode on, skipping scrape")
        await asyncio.sleep(5*60)


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

    await asyncio.gather(
        hassLoop(token, url),
        scrapeLoop(),
        )


async def connect(token: str, url: str, session: ClientSession) -> asyncio.Task[None]:
    """Connect to the server."""
    websocket_url =  f"{url}/api/websocket"
    client = HomeAssistantClient(websocket_url, token, session)
    await client.connect()
    listener = asyncio.create_task(client.start_listening())
    await client.subscribe_entities(art_mode_toggle, ["input_boolean.tv_art_mode"])
    return listener

def mustEnv(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise Exception(f"Must set {v}")
    return v

async def scrape() -> bytes:
    config = scraper.Config(
        url=mustEnv("FRAME_SCRAPER_URL"),
        username=mustEnv("FRAME_SCRAPER_USERNAME"),
        password=mustEnv("FRAME_SCRAPER_PASSWORD"),
        dashboardPath=mustEnv("FRAME_SCRAPER_DASHBOARD_URL"),
        )

    loop = asyncio.get_running_loop()
    wrapped = partial(scraper.scrape, config, True)
    screenshot = await loop.run_in_executor(None, wrapped)

    return screenshot


def art_mode_toggle(event: EntityStateEvent) -> None:
    global artMode
    try:
        st = event['a']['input_boolean.tv_art_mode']['s']
        artMode = st == 'on'
        LOGGER.debug("art mode changed: %s", artMode)
        return
    except KeyError:
        pass

    try:
        st = event['c']['input_boolean.tv_art_mode']['+']['s']
        artMode = st == 'on'
        LOGGER.debug("art mode changed: %s", artMode)
    except KeyError:
        pass


def main() -> None:
    asyncio.run(start())


if __name__ == "__main__":
    main()
