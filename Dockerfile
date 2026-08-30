# NR1 Agent
FROM python:3.10-slim

WORKDIR /app

# Evita baixar a distribuição CUDA do PyTorch; o agente usa apenas CPU.
RUN pip install --no-cache-dir --no-deps \
    --index-url https://download.pytorch.org/whl/cpu \
    torch==2.3.1+cpu
COPY pyproject.toml .
COPY nr1_agent/ ./nr1_agent/
COPY scripts/ ./scripts/
COPY frontend/ ./frontend/
COPY data/ ./data/

RUN pip install --no-cache-dir --prefer-binary .

EXPOSE 8000

CMD ["uvicorn", "nr1_agent.main:app", "--host", "0.0.0.0", "--port", "8000"]
