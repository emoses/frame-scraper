# Frame Scraper

Use selenium to capture a screenshot of a home assistant dashboard, and then upload it as an Art Mode image to a Samsung Frame TV.

Many thanks to [@NickWateron](https://github.com/NickWaterton) for https://github.com/NickWaterton/samsung-tv-ws-api

## Requirements

You'll need go and docker to build

## Building

Run

```shell
make docker
```

to build the Go selenium app and two docker containers you need

## Configuration

Add a .env file in the root that looks like this:

```
FRAME_SCRAPER_URL=https://your.home.assistant.example
FRAME_SCRAPER_USERNAME=<HA username>
FRAME_SCRAPER_PASSWORD=<HA password>
FRAME_IP=<The IP of you Frame TV>
```

## Run

Run

```shell
./scrape.sh
```
