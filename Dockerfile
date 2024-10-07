FROM selenium/standalone-chromium:129.0 as selenium

COPY build/frame-scraper-linux .

ENV FRAME_SCRAPER_URL https://hass.coopermoses.com

USER root
RUN mkdir -p -m 0777 /output

USER seluser

ENTRYPOINT ./frame-scraper-linux
