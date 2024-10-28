FROM python:3.12-bookworm AS python-packages
RUN apt update && apt install git

ADD Pipfile.lock Pipfile .
RUN pip install --upgrade pip && pip install pipenv && PIPENV_VENV_IN_PROJECT=true pipenv install --ignore-pipfile


FROM mcr.microsoft.com/playwright:v1.48.1-noble
RUN apt-get update && apt-get install -qqy python3.12
COPY --from=python-packages /.venv /app/.venv
RUN ln -sf $(which python3) /app/.venv/bin/python
WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH"
COPY ./*.py /app/

ENTRYPOINT ["/app/.venv/bin/python", "main.py"]
