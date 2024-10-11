FROM python:3.11-alpine

RUN pip install pdm
COPY pyproject.toml /scraper/
COPY pdm.lock /scraper/
WORKDIR /scraper
RUN pdm install

COPY src /scraper/src
EXPOSE 8000

ENTRYPOINT ["pdm", "run", "src/bandcamp_link_scraper/api.py"]
