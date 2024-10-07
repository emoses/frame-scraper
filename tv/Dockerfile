FROM python:3.11-alpine AS base

FROM base AS python-packages
RUN apk update && apk add git
COPY Pipfile* .
RUN pip install pipenv && PIPENV_VENV_IN_PROJECT=true pipenv install --ignore-pipfile

FROM base AS runtime
COPY --from=python-packages /.venv /.venv
ENV PATH="/.venv/bin:$PATH"
WORKDIR /app
COPY main.py /app/main.py

ENTRYPOINT ["python", "main.py"]
