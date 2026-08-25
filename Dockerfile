# NR1 Agent
FROM python:3.10-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

COPY app/ ./app/
COPY frontend/ ./frontend/
COPY data/ ./data/

EXPOSE 8000

CMD ["nr1-agent"]