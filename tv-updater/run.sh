#!/usr/bin/env bash

docker run -v $(pwd)/../scraper/output:/output --env-file  ../.env emoses/tv-updater $@
