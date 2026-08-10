FROM python:3.13-slim

RUN pip install uv --no-cache-dir

WORKDIR /app

COPY pyproject.toml uv.lock* ./

RUN uv sync --no-dev --no-cache

COPY . .

CMD ["uv", "run", "src/main.py"]