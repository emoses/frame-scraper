#!/usr/bin/env bash

docker run -v $(PWD)/../scraper/output:/output --env-file  ../.env emoses/tv-updater $@
