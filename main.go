package main

import (
	"fmt"
	"os"

	"github.com/tebeka/selenium"
	"github.com/tebeka/selenium/chrome"
)

func main() {
	opts := []selenium.ServiceOption{
		selenium.ChromeDriver("/bin/chromedriver"),
		selenium.Output(os.Stderr),
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
			},
		},
	)

	wd, err := selenium.NewRemote(caps, fmt.Sprintf("http://localhost:4444/wd/hub"))
	if err != nil {
		panic(fmt.Sprintf("Error starting selenium: %s", err.Error()))
	}
	defer wd.Quit()

	url, ok := os.LookupEnv("FRAME_SCRAPER_URL")
	if !ok {
		panic("Must provide FRAME_SCRAPER_URL in environment")
	}

	if err := wd.Get(url); err != nil {
		panic(fmt.Sprintf("Unable to nav to hass: %s", err.Error()))
	}

	data, err := wd.Screenshot()
	if err != nil {
		panic(fmt.Sprintf("Unable to screenshot: %s", err.Error()))
	}

	if err := os.WriteFile("output/screen.png", data, 0644); err != nil {
		panic(fmt.Sprintf("Error writing screenshot: %s", err.Error()))
	}

}
