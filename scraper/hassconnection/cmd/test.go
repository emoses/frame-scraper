package main

import (
	"context"
	"log/slog"
	"os"
	"time"

	"git.emoses.org/frame-scraper/hassconnection"
)

func main() {
	h := slog.NewTextHandler(os.Stderr, &slog.HandlerOptions{Level: slog.LevelDebug})
	slog.SetDefault(slog.New(h))

	token, ok := os.LookupEnv("HASS_TOKEN")
	if !ok {
		slog.Error("No HASS_TOKEN provided")
		os.Exit(1)
	}
	config := &hassconnection.Config{
		Address: "wss://hass.coopermoses.com/api/websocket",
		Token:   token,
	}

	c := hassconnection.New(config)
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	go func() {
		if err := c.Run(ctx); err != nil {
			slog.Error("Error calling Run", "err", err)
		}
		slog.Info("Run ended")
	}()

	<-c.Ready()

	allStates, err := c.GetStates()
	if err != nil {
		slog.Error("Error from getState", "err", err)
		cancel()
		os.Exit(1)
	}

	slog.Info("Got states", "len", len(allStates))
	slog.Info("First state", "state", allStates[0])

	states, closer, err := c.Subscribe("state_changed")
	if err != nil {
		slog.Error("Error subscribing", "err", err)
		cancel()
		os.Exit(1)
	}

	go func() {
		for {
			select {
			case <-ctx.Done():
				return
			case msg, ok := <-states:
				if !ok {
					return
				}
				slog.Info("State changed", "state", msg)
			}
		}
	}()

	<-time.After(5 * time.Second)
	closer()
	cancel()

}
