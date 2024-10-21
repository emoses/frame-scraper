docker:
	docker build -t emoses/hass-scraper-py .

run:
	mkdir -p output
	docker run --shm-size="2g" -v ${PWD}/output:/output --env-file  ./.env emoses/hass-scraper-py
