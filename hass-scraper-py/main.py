import asyncio
import logging
import sys
import os
import re

from dotenv import load_dotenv
from functools import partial
from aiohttp import ClientSession
from typing import Tuple

from hass_client import HomeAssistantClient
from hass_client.exceptions import ConnectionFailed
from hass_client.models import EntityStateEvent

import scraper
from frame import Tv
from db import Db

DEFAULT_SCRAPE_DELAY_S = 5*60
LOGGER = logging.getLogger()

ART_MODE_EID = "input_boolean.tv_art_mode"
TV_EID = "media_player.frame_tv"

artMode = False
artModeCond = asyncio.Condition()
tvOn = False
tvOnCond = asyncio.Condition()


async def hassLoop(token: str, url: str) -> None:
    while True:
        try:
            async with ClientSession() as session:
                listener = await connect(token, url, session)
                await listener
        except ConnectionFailed as e:
            LOGGER.warn("Connection error, reconnecting", e)
            await asyncio.sleep(60)

async def scrapeLoop(delay: float | None, tv: Tv, db: Db) -> None:
    global artMode, tvOn
    while True:
        async with tvOnCond:
            await tvOnCond.wait_for(lambda: tvOn and not artMode)

        screenshot = await scrape()
        next_name = tv.upload(screenshot)
        db.add(next_name)
        await clean(tv, db)
        await asyncio.sleep(delay or DEFAULT_SCRAPE_DELAY_S)

async def artModeLoop(tv: Tv) -> None:
    global artMode, tvOn
    while True:
        async with tvOnCond:
            await tvOnCond.wait_for(lambda: artMode and tvOn)
        tv.select('MY_F0105')
        async with tvOnCond:
            await tvOnCond.wait_for(lambda: not(artMode and tvOn))

async def clean(tv: Tv, db: Db) -> None:
    oldFiles = db.list()[:-1]
    for i in range(0, len(oldFiles), 5):
        chunk = oldFiles[i:i+5]
        LOGGER.debug("Deleting %r", chunk)
        tv.delete(chunk)
        db.delete(chunk)

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

    delayStr = os.getenv("FRAME_SCRAPER_INTERVAL_SEC")
    delay: float | None = None
    if delayStr:
        delay = float(delayStr)

    frame_ip = os.getenv("FRAME_SCRAPER_IP")
    if not frame_ip:
        LOGGER.error("Missing env var FRAME_SCRAPER_IP")
        sys.exit(1)
    tv = Tv(frame_ip)

    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("hass_client").setLevel(logging.INFO)

    db = Db('/data/data.db')

    await asyncio.gather(
        hassLoop(token, url),
        scrapeLoop(delay=delay, tv=tv, db=db),
        artModeLoop(tv=tv),
        )


async def connect(token: str, url: str, session: ClientSession) -> asyncio.Task[None]:
    """Connect to the server."""
    global artMode, tvOn
    websocket_url =  f"{url}/api/websocket"
    client = HomeAssistantClient(websocket_url, token, session)
    await client.connect()
    listener = asyncio.create_task(client.start_listening())
    states = await client.get_states()
    for s in states:
        if s["entity_id"] == ART_MODE_EID:
            artMode = s["state"] == "on"
            LOGGER.debug("Art mode initial state: %s", artMode)
        elif s["entity_id"] == TV_EID:
            val = s["state"] == "on"
            await set_tv_on(val)
            LOGGER.debug("Tv initial state: %s", val)
    await client.subscribe_entities(art_mode_toggle, [ART_MODE_EID])
    await client.subscribe_entities(tv_on_toggle, [TV_EID])
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

def state_from_evt(eid: str, event: EntityStateEvent) -> bool | None:
    try:
        st = event['a'][eid]['s']
        return st == 'on'
    except KeyError:
        pass

    try:
        st = event['c'][eid]['+']['s']
        return st == 'on'
    except KeyError:
        pass

    return None



def tv_on_toggle(event: EntityStateEvent) -> None:
    val = state_from_evt(TV_EID, event)
    if val != None:
        task = asyncio.create_task(set_tv_on(val))
        asyncio.get_running_loop().run_until_complete(task)

def art_mode_toggle(event: EntityStateEvent) -> None:
    val = state_from_evt(ART_MODE_EID, event)
    if val != None:
        task = asyncio.create_task(set_art_mode(val))
        asyncio.get_running_loop().run_until_complete(task)

async def set_art_mode(val: bool) -> None:
    global artMode
    async with tvOnCond:
        artMode = val
        LOGGER.debug("art mode updated: %s", artMode)
        tvOnCond.notify_all()

async def set_tv_on(val: bool) -> None:
    global tvOn
    async with tvOnCond:
        tvOn = val
        LOGGER.debug("tvOn updated: %s", tvOn)
        tvOnCond.notify_all()



def main() -> None:
    asyncio.run(start())


if __name__ == "__main__":
    main()
