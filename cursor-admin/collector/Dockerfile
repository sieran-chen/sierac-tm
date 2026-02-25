FROM python:3.12-slim

RUN pip install --no-cache-dir poetry \
    && poetry config virtualenvs.create false

WORKDIR /app

COPY collector/pyproject.toml collector/poetry.lock ./
RUN poetry install --no-dev --no-interaction --no-root

COPY collector/ ./
COPY db/ /db/

ENV PYTHONUNBUFFERED=1

EXPOSE 8000
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
