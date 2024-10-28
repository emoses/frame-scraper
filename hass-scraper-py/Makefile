docker:
	docker build -f Dockerfile.playwright -t emoses/hass-scraper-py .

run:
	docker run --shm-size="2g" -v ${PWD}/data:/data --env-file  ./.env emoses/hass-scraper-py
