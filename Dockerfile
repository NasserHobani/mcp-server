FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt pyproject.toml README.md /app/
COPY cs_ai_bridge_mcp /app/cs_ai_bridge_mcp

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir .

EXPOSE 8000

CMD fastmcp run cs_ai_bridge_mcp/server.py:mcp --transport streamable-http --host 0.0.0.0 --port 8000