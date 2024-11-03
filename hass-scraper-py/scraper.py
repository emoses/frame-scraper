from playwright.async_api import async_playwright, Playwright, TimeoutError as PlaywrightTimeoutError
import dataclasses
import logging
import asyncio
import argparse

from dotenv import load_dotenv

from util import mustEnv, openb

CONTEXT_FILE = '/data/playwright'

LOGGER = logging.Logger(__name__)

@dataclasses.dataclass
class Config:
    username: str
    password: str
    url: str
    dashboardPath: str

async def scrape(
        config: Config,
        ) -> bytes:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch_persistent_context(
            CONTEXT_FILE,
            headless=True,
            viewport={
                "width": 1728,
                "height": 972,
            },
            device_scale_factor=2.2222222222222,
            args=[
                "--disable-gpu",
            ])
        page = await browser.new_page()
        await page.goto(f'{config.url}/{config.dashboardPath}')
        outer = page.locator('home-assistant')
        try:
            await outer.wait_for(timeout=2000)
        except PlaywrightTimeoutError:
            LOGGER.info("Logging in")
            # This means we were redirected to the login page
            await page.locator("[name='username']").fill(config.username)
            pw = page.locator("[name='password']")
            await pw.fill(config.password)
            await pw.press("Enter")
            await page.locator("home-assistant").wait_for()
            await page.goto(f'{config.url}/{config.dashboardPath}')
        await page.locator("ha-card.type-custom-week-planner-card .day").first.wait_for()

        return await page.screenshot()


async def scrape_main() -> None:
    logging.basicConfig(
        format='%(asctime)s %(levelname)-8s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        level=logging.DEBUG,
    )
    load_dotenv()

    parser = argparse.ArgumentParser()
    parser.add_argument("filename", default="/output/scrape.png")
    args = parser.parse_args()


    config = Config(
        url=mustEnv("FRAME_SCRAPER_URL"),
        username=mustEnv("FRAME_SCRAPER_USERNAME"),
        password=mustEnv("FRAME_SCRAPER_PASSWORD"),
        dashboardPath=mustEnv("FRAME_SCRAPER_DASHBOARD_URL"),
        )

    file = await asyncio.create_task(scrape(config))
    with open(args.filename, 'wb') as f:
        f.write(file)

if __name__ == '__main__':
    asyncio.run(scrape_main())
