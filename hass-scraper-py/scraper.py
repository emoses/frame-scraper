from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.remote.webdriver import WebDriver
import dataclasses
import time
import asyncio

@dataclasses.dataclass
class Config:
    username: str
    password: str
    url: str
    dashboardPath: str

def start_browser() -> WebDriver:
    options = webdriver.ChromeOptions()
    for arg in [
            "--headless",
            "--disable-gpu",
            # Use half-size but scale to 2x; this gives us expected size at high dpi
            "--window-size=1920,1080",
            "--force-device-scale-factor=2",
        ]:
        options.add_argument(arg)
    wd = webdriver.Chrome(
        options=options,
        service=Service(executable_path="/bin/chromedriver"),
    )

    wd.implicitly_wait(10)
    return wd

def scrape(
        config: Config,
        debug: bool = False,
) -> bytes:
    wd = start_browser()
    wd.get(config.url)

    usernameEl = wd.find_element(By.NAME, "username")
    usernameEl.send_keys(config.username)

    passwordEl = wd.find_element(By.NAME, "password")
    passwordEl.send_keys(config.password + "\n")

    wd.find_elements(By.TAG_NAME, "home-assistant")
    wd.get(f'{config.url}/{config.dashboardPath}')
    wd.find_elements(By.TAG_NAME, "home-assistant")

    # TODO investigate switching to playwrite, which has better shadow dom functions
    time.sleep(5)

    return wd.get_screenshot_as_png()
