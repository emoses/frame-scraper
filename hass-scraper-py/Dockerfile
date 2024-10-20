FROM python:3.13-alpine AS base

FROM base AS python-packages
RUN apk update && apk add git
COPY Pipfile* .
RUN pip install pipenv && PIPENV_VENV_IN_PROJECT=true pipenv install --ignore-pipfile


FROM selenium/standalone-chromium:129.0 as selenium
COPY --from=python-packages /.venv /.venv

ENV PATH="/.venv/bin:$PATH"
WORKDIR /app
COPY *.py /app/

ENTRYPOINT ["python", "main.py"]
