build-linux: *.go
	mkdir -p build
	GOOS=linux go build -o build/frame-scraper-linux

docker: build-linux
	docker build -t emoses/frame-scraper .

run:
	docker run --shm-size="2g" -v $(PWD)/output:/output --env-file  ../.env emoses/frame-scraper
