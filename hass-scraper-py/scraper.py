from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.remote.webdriver import WebDriver

def start_browser() -> WebDriver:
    wd = webdriver.Chrome(
        service=Service(service_args=[
            "--headless",
            "--disable-gpu",
            # Use half-size but scale to 2x; this gives us expected size at high dpi
            "--window-size=1920,1080",
            "--force-device-scale-factor=2",
        ]),
    )

    wd.implicitly_wait(10)
    return wd

def scrape(
        username: str,
        password: str,
        url: str,
        dashboardPath: str,
        debug: bool = False,
) -> bytes:
    wd = start_browser()
    wd.get(url)

    usernameEl = wd.find_element(By.NAME, "username")
    usernameEl.send_keys(username)

    passwordEl = wd.find_element(By.NAME, "password")
    passwordEl.send_keys(password)

    wd.find_elements(By.TAG_NAME, "home-assistant")
    wd.get(f'{url}/{dashboardPath}')
    wd.find_elements(By.TAG_NAME, "home-assistant")

    return wd.get_screenshot_as_png()
