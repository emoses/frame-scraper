#!/usr/bin/env bash

set -uxeo pipefail

pushd scraper/
make run

popd

PREV=""
if [ -f previous-upload ]; then
    PREV=$(<previous-upload)
fi

pushd tv-updater/
./run.sh upload /output/screen.png > ../previous-upload

if [ -n "$PREV" ]; then
    ./run.sh delete "$PREV"
fi
