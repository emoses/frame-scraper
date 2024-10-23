docker:
	docker build -t emoses/hass-scraper-py .

run:
	mkdir -p output
	docker run --shm-size="2g" -v ${PWD}/output:/output -v ${PWD}/data:/data --env-file  ./.env emoses/hass-scraper-py
