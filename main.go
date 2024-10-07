package main

import (
	"fmt"
	"os"
	"time"

	"github.com/tebeka/selenium"
	"github.com/tebeka/selenium/chrome"
)

func main() {
	opts := []selenium.ServiceOption{
		selenium.ChromeDriver("/bin/chromedriver"),
		selenium.Output(os.Stderr),
	}

	username, ok := os.LookupEnv("FRAME_SCRAPER_USERNAME")
	if !ok {
		fmt.Fprintf(os.Stderr, "Must supply FRAME_SCRAPER_USERNAME")
		os.Exit(1)
	}
	password, ok := os.LookupEnv("FRAME_SCRAPER_PASSWORD")
	if !ok {
		fmt.Fprintf(os.Stderr, "Must supply FRAME_SCRAPER_PASSWORD")
		os.Exit(1)
	}

	selenium.SetDebug(true)
	service, err := selenium.NewChromeDriverService("/bin/chromedriver", 4444, opts...)
	if err != nil {
		panic(fmt.Sprintf("Unable to start selenium service: %s", err.Error()))
	}
	defer service.Stop()

	caps := selenium.Capabilities{
		"browserName": "chromium",
	}
	caps.AddChrome(
		chrome.Capabilities{
			Path: "/bin/chromium",
			Args: []string{
				"--headless",
				"--disable-gpu",
				"--window-size=3840x2160",
			},
		},
	)

	wd, err := selenium.NewRemote(caps, fmt.Sprintf("http://localhost:4444/wd/hub"))
	if err != nil {
		panic(fmt.Sprintf("Error starting selenium: %s", err.Error()))
	}
	defer wd.Quit()
	wd.SetImplicitWaitTimeout(10 * time.Second)

	url, ok := os.LookupEnv("FRAME_SCRAPER_URL")
	if !ok {
		panic("Must provide FRAME_SCRAPER_URL in environment")
	}

	if err := wd.Get(url); err != nil {
		panic(fmt.Sprintf("Unable to nav to hass: %s", err.Error()))
	}

	usernameEl, err := wd.FindElement(selenium.ByName, "username")
	if err != nil {
		panic(fmt.Sprintf("Can't find username field"))
	}
	if err := usernameEl.SendKeys(username); err != nil {
		panic(fmt.Sprintf("Error sending keys to username: %s", err.Error()))
	}
	passwordEl, err := wd.FindElement(selenium.ByName, "password")
	if err != nil {
		panic(fmt.Sprintf("Can't find password field"))
	}
	if err := passwordEl.SendKeys(password + "\n"); err != nil {
		panic(fmt.Sprintf("Error sending keys to password: %s", err.Error()))
	}

	if _, err := wd.FindElements(selenium.ByTagName, "home-assistant"); err != nil {
		panic(fmt.Sprintf("Error waiting for main page load: %s", err.Error()))
	}
	// TODO env var
	if err := wd.Get(url + "/lovelace/frame?kiosk"); err != nil {
		panic(fmt.Sprintf("Error opening frame page: %s", err.Error()))
	}
	if _, err := wd.FindElements(selenium.ByTagName, "home-assistant"); err != nil {
		panic(fmt.Sprintf("Error waiting for main page load: %s", err.Error()))
	}

	time.Sleep(10 * time.Second) //yeah yeah I know

	data, err := wd.Screenshot()
	if err != nil {
		panic(fmt.Sprintf("Unable to screenshot: %s", err.Error()))
	}

	if err := os.WriteFile("output/screen.png", data, 0644); err != nil {
		panic(fmt.Sprintf("Error writing screenshot: %s", err.Error()))
	}

}
