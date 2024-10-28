from playwright.async_api import async_playwright, Playwright, TimeoutError as PlaywrightTimeoutError
import dataclasses
import logging

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
                "width": 1920,
                "height": 1080,
            },
            device_scale_factor=2,
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
