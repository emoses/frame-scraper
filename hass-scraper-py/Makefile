docker:
	docker build -t emoses/hass-scraper-py .

run:
	docker run --shm-size="2g" -v ${PWD}/data:/data --env-file  ./.env emoses/hass-scraper-py

scrape:
	docker run --shm-size="2g" -v ${PWD}/output:/output --env-file  ./.env --entrypoint "/app/.venv/bin/python" emoses/hass-scraper-py scraper.py /output/scrape.png
