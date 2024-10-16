package scrape

import (
	"fmt"
	"os"
	"strings"
	"time"

	"github.com/tebeka/selenium"
	"github.com/tebeka/selenium/chrome"
)

type Config struct {
	HassUsername  string
	HassPassword  string
	HassUrl       string
	DashboardPath string
	SeleniumDebug bool
}

func Scrape(config Config) ([]byte, error) {
	opts := []selenium.ServiceOption{
		selenium.ChromeDriver("/bin/chromedriver"),
		selenium.Output(os.Stderr),
	}

	dashboardUrl, _ := strings.CutPrefix(config.DashboardPath, "/")

	if config.SeleniumDebug {
		selenium.SetDebug(true)
	} else {
		selenium.SetDebug(false)
	}

	service, err := selenium.NewChromeDriverService("/bin/chromedriver", 4444, opts...)
	if err != nil {
		return nil, fmt.Errorf("Unable to start selenium service: %w", err)
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
		return nil, fmt.Errorf("Error starting selenium: %w", err)
	}
	defer wd.Quit()
	wd.SetImplicitWaitTimeout(10 * time.Second)

	if err := wd.Get(config.HassUrl); err != nil {
		fmt.Sprintf("Unable to nav to hass: %w", err)
	}

	usernameEl, err := wd.FindElement(selenium.ByName, "username")
	if err != nil {
		return nil, fmt.Errorf("Can't find username field: %w", err)
	}
	if err := usernameEl.SendKeys(config.HassUsername); err != nil {
		return nil, fmt.Errorf("Error sending keys to username: %w", err)
	}
	passwordEl, err := wd.FindElement(selenium.ByName, "password")
	if err != nil {
		return nil, fmt.Errorf("Can't find password field: %w", err)
	}
	if err := passwordEl.SendKeys(config.HassPassword + "\n"); err != nil {
		return nil, fmt.Errorf("Error sending keys to password: %w", err)
	}

	if _, err := wd.FindElements(selenium.ByTagName, "home-assistant"); err != nil {
		return nil, fmt.Errorf("Error waiting for main page load: %w", err)
	}
	if err := wd.Get(fmt.Sprintf("%s/%s", config.HassUrl, dashboardUrl)); err != nil {
		return nil, fmt.Errorf("Error opening frame page: %w", err)
	}
	if _, err := wd.FindElements(selenium.ByTagName, "home-assistant"); err != nil {
		return nil, fmt.Errorf("Error waiting for main page load: %s", err)
	}

	time.Sleep(5 * time.Second) //yeah yeah I know

	data, err := wd.Screenshot()
	if err != nil {
		return nil, fmt.Errorf("Unable to screenshot: %w", err)
	}

	return data, nil
}
