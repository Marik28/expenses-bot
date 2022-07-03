FROM python:3.10

RUN pip install -U pip setuptools && pip install --ignore-installed poetry

WORKDIR /app

COPY pyproject.toml poetry.lock /app/
COPY src/ /app/

RUN poetry install

ENTRYPOINT ["poetry", "run"]