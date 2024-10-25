import asyncio
import logging
import sys
import os
import re
import tomllib
import random

from dotenv import load_dotenv
from functools import partial
from aiohttp import ClientSession
from typing import TypedDict, List, cast, Generator, TypeVar

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

class ScraperConfig(TypedDict):
    interval_sec: float

class ArtConfig(TypedDict):
    files: List[str]
    rotate_interval_min: float
    shuffle: bool

class SystemConfig(TypedDict):
    logging: str

class Config(TypedDict):
    system: SystemConfig
    scraper: ScraperConfig
    art: ArtConfig


class App:
    token: str
    url: str
    tv: Tv
    db: Db
    config: Config


async def hassLoop(app: App) -> None:
    while True:
        try:
            async with ClientSession() as session:
                listener = await connect(app.token, app.url, session)
                await listener
        except ConnectionFailed as e:
            LOGGER.warn("Connection error, reconnecting", e)
            await asyncio.sleep(60)

async def scrapeLoop(app: App) -> None:
    global artMode, tvOn
    while True:
        try:
            async with tvOnCond:
                await tvOnCond.wait_for(lambda: tvOn and not artMode)

            screenshot = await scrape()
            next_name = app.tv.upload(screenshot)
            app.db.add(next_name)
            await clean(app)
            await asyncio.sleep(app.config["scraper"]["interval_sec"] or DEFAULT_SCRAPE_DELAY_S)
        except Exception as e:
            LOGGER.warn("Error in scrape loop: %r", e)
            await asyncio.sleep(5)

T = TypeVar("T")
def loopList(ll: List[T]) -> Generator[T, None, None]:
    while True:
        for l in ll:
            yield l

async def artModeLoop(app: App) -> None:
    global artMode, tvOn
    arts = app.config["art"]["files"].copy()
    if len(arts) < 1:
        LOGGER.warn("No art to show.  Add art.files in the config")
    if app.config["art"]["shuffle"]:
        random.shuffle(arts)
    artsGen = loopList(arts)
    while True:
        try:
            async with tvOnCond:
                await tvOnCond.wait_for(lambda: artMode and tvOn)
            app.tv.select(next(artsGen))
            async with tvOnCond:
                tasks = [asyncio.create_task(t) for t in [
                    tvOnCond.wait_for(lambda: not(artMode and tvOn)),
                    asyncio.sleep(app.config["art"]["rotate_interval_min"]*60),
                    ]]
                _, leftover = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                for task in leftover:
                    task.cancel()
        except Exception as e:
            LOGGER.warn("Error in art mode loop, restarting: %r", e)
            await asyncio.sleep(5)


async def clean(app: App) -> None:
    oldFiles = app.db.list()[:-1]
    for i in range(0, len(oldFiles), 5):
        chunk = oldFiles[i:i+5]
        LOGGER.debug("Deleting %r", chunk)
        app.tv.delete(chunk)
        app.db.delete(chunk)

async def start() -> None:
    """Run main."""

    load_dotenv()

    app = App()

    token = os.getenv("HASS_TOKEN")
    if not token:
        LOGGER.error("Missing env var HASS_TOKEN")
        sys.exit(1)
    app.token = token


    url = os.getenv("HASS_URL")
    if not url:
        LOGGER.error("Missing env var HASS_URL")
        sys.exit(1)
    url = re.sub("^http", "ws", url)
    if not url.startswith("ws"):
        url = f'ws://{url}'
    app.url = url

    frame_ip = os.getenv("FRAME_SCRAPER_IP")
    if not frame_ip:
        LOGGER.error("Missing env var FRAME_SCRAPER_IP")
        sys.exit(1)
    app.tv = Tv(frame_ip)

    configPath = os.getenv("FRAME_SCRAPER_CONFIG")
    if not configPath:
        configPath = '/data/config.toml'
    try:
        with open(configPath, 'rb') as f:
            app.config = cast(Config, tomllib.load(f))
    except Exception as e:
        LOGGER.error("Error loading config from %s: %r", configPath, e)

    logLevel = app.config["system"].get("logging", "INFO")
    if not logLevel in logging.getLevelNamesMapping():
        LOGGER.error("Invalid log level in config: %s", logLevel)
        logLevel = "INFO"

    app.db = Db('/data/data.db')

    logging.basicConfig(
        format='%(asctime)s %(levelname)-8s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        level=logging.getLevelNamesMapping()[logLevel],
    )
    logging.getLogger("hass_client").setLevel(logging.INFO)



    await asyncio.gather(
        hassLoop(app),
        scrapeLoop(app),
        artModeLoop(app),
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



async def tv_on_toggle(event: EntityStateEvent) -> None:
    val = state_from_evt(TV_EID, event)
    if val != None:
        await set_tv_on(val)

async def art_mode_toggle(event: EntityStateEvent) -> None:
    val = state_from_evt(ART_MODE_EID, event)
    if val != None:
        await set_art_mode(val)

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
