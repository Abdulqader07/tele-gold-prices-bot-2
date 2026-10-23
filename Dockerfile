FROM python:3.13-slim

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir .

COPY src ./src

RUN useradd -m app && chown -R app:app /app
USER app

ENV PYTHONUNBUFFERED=1

CMD ["python", "src/main.py"]