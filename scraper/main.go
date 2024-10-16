package main

import (
	"fmt"
	"os"
	"strings"

	"git.emoses.org/frame-scraper/scrape"
)

const OutputPath = "./output/scrape.png"

func GetConfig() (&scrape.Config, error) {
	username, ok := os.LookupEnv("FRAME_SCRAPER_USERNAME")
	if !ok {
		return nil, fmt.Errorf("Must supply FRAME_SCRAPER_USERNAME")
	}
	password, ok := os.LookupEnv("FRAME_SCRAPER_PASSWORD")
	if !ok {
		return nil, fmt.Errorf("Must supply FRAME_SCRAPER_PASSWORD")
	}
	url, ok := os.LookupEnv("FRAME_SCRAPER_URL")
	if !ok {
		return nil, fmt.Errorf("Must provide FRAME_SCRAPER_URL in environment")
	}
	dashboardUrl, ok := os.LookupEnv("FRAME_SCRAPER_DASHBOARD_URL")
	if !ok {
		return nil, fmt.Errorf("Must provide FRAME_SCRAPER_DASHBOARD_URL")
	}
	// Trim leading "/" if any
	dashboardUrl, _ = strings.CutPrefix(dashboardUrl, "/")

	_, debug := os.LookupEnv("DEBUG")

	return &scrape.Config{
		HassUsername:  username,
		HassPassword:  password,
		HassUrl:       url,
		DashboardPath: dashboardUrl,
		SeleniumDebug: debug,
	}, nil
}


func main() {

	config, err := GetConfig()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v", err)
		os.Exit(2)
	}

	img, err := scrape.Scrape(config)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error scraping: %v", err)
		os.Exit(1)
	}

	if err := os.WriteFile(OutputPath, img, 0644); err != nil {
		fmt.Fprintf(os.Stderr, "Error writing output file to %s: %v", OutputPath, err)
		os.Exit(1)
	}
}
