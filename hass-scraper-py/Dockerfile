FROM python:3.12-alpine AS python-packages
RUN apk update && apk add git

ADD Pipfile.lock Pipfile .
RUN pip install pipenv && PIPENV_VENV_IN_PROJECT=true pipenv install --ignore-pipfile


FROM selenium/standalone-chromium:129.0
RUN sudo apt-get update && sudo apt-get install -qqy python3.12
COPY --from=python-packages /.venv /app/.venv
RUN sudo ln -sf $(which python3) /app/.venv/bin/python
WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH"
COPY ./*.py /app/

ENTRYPOINT ["/app/.venv/bin/python", "main.py"]
