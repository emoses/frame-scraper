build-linux: *.go
	mkdir -p build
	GOOS=linux go build -o build/frame-scraper-linux

docker: build-linux
	docker build -t emoses/frame-scraper .

run:
	docker run --env-file ./.env emoses/frame-scraper
