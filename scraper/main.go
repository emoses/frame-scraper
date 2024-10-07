package main

import (
	"fmt"
	"os"
	"strings"
	"time"

	"github.com/tebeka/selenium"
	"github.com/tebeka/selenium/chrome"
)

func run() error {
	opts := []selenium.ServiceOption{
		selenium.ChromeDriver("/bin/chromedriver"),
		selenium.Output(os.Stderr),
	}

	username, ok := os.LookupEnv("FRAME_SCRAPER_USERNAME")
	if !ok {
		return fmt.Errorf("Must supply FRAME_SCRAPER_USERNAME")
	}
	password, ok := os.LookupEnv("FRAME_SCRAPER_PASSWORD")
	if !ok {
		return fmt.Errorf("Must supply FRAME_SCRAPER_PASSWORD")
	}
	url, ok := os.LookupEnv("FRAME_SCRAPER_URL")
	if !ok {
		return fmt.Errorf("Must provide FRAME_SCRAPER_URL in environment")
	}
	dashboardUrl, ok := os.LookupEnv("FRAME_SCRAPER_DASHBOARD_URL")
	if !ok {
		return fmt.Errorf("Must provide FRAME_SCRAPER_DASHBOARD_URL")
	}
	// Trim leading "/" if any
	dashboardUrl, _ = strings.CutPrefix(dashboardUrl, "/")

	if _, ok := os.LookupEnv("DEBUG"); ok {
		selenium.SetDebug(true)
	} else {
		selenium.SetDebug(false)
	}

	service, err := selenium.NewChromeDriverService("/bin/chromedriver", 4444, opts...)
	if err != nil {
		return fmt.Errorf("Unable to start selenium service: %w", err)
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
				// Use half-size but scale to 2x; this gives us expected size at high dpi
				"--window-size=1920,1080",
				"--force-device-scale-factor=2",
			},
		},
	)

	wd, err := selenium.NewRemote(caps, fmt.Sprintf("http://localhost:4444/wd/hub"))
	if err != nil {
		return fmt.Errorf("Error starting selenium: %w", err)
	}
	defer wd.Quit()
	wd.SetImplicitWaitTimeout(10 * time.Second)

	if err := wd.Get(url); err != nil {
		fmt.Sprintf("Unable to nav to hass: %w", err)
	}

	usernameEl, err := wd.FindElement(selenium.ByName, "username")
	if err != nil {
		return fmt.Errorf("Can't find username field: %w", err)
	}
	if err := usernameEl.SendKeys(username); err != nil {
		return fmt.Errorf("Error sending keys to username: %w", err)
	}
	passwordEl, err := wd.FindElement(selenium.ByName, "password")
	if err != nil {
		return fmt.Errorf("Can't find password field: %w", err)
	}
	if err := passwordEl.SendKeys(password + "\n"); err != nil {
		return fmt.Errorf("Error sending keys to password: %w", err)
	}

	if _, err := wd.FindElements(selenium.ByTagName, "home-assistant"); err != nil {
		return fmt.Errorf("Error waiting for main page load: %w", err)
	}
	if err := wd.Get(fmt.Sprintf("%s/%s", url, dashboardUrl)); err != nil {
		return fmt.Errorf("Error opening frame page: %w", err)
	}
	if _, err := wd.FindElements(selenium.ByTagName, "home-assistant"); err != nil {
		return fmt.Errorf("Error waiting for main page load: %s", err)
	}

	time.Sleep(5 * time.Second) //yeah yeah I know

	data, err := wd.Screenshot()
	if err != nil {
		return fmt.Errorf("Unable to screenshot: %w", err)
	}

	if err := os.WriteFile("output/screen.png", data, 0644); err != nil {
		return fmt.Errorf("Error writing screenshot: %w", err)
	}

	return nil

}

func main() {
	err := run()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v", err)
		os.Exit(1)
	}
}
