FROM selenium/standalone-chromium:129.0 as selenium

COPY build/frame-scraper-linux .

USER root
RUN mkdir -p -m 0777 /output

USER seluser

ENTRYPOINT ./frame-scraper-linux
