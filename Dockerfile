FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir flexorch-mcp

ENV MCP_TRANSPORT=http
ENV PORT=8080

EXPOSE 8080

ENTRYPOINT ["flexorch-mcp"]
