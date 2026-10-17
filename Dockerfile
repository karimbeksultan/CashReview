FROM node:22-alpine AS frontend
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 CASH_REVIEW_MODEL_DIR=/models CASH_REVIEW_DATA_DIR=/data
WORKDIR /app
COPY backend/requirements.lock.txt /app/requirements.lock.txt
RUN pip install --no-cache-dir -r requirements.lock.txt && useradd --uid 10001 --create-home reviewer && mkdir /data /models && chown reviewer:reviewer /data /models
COPY --chown=reviewer:reviewer backend/ /app/backend/
COPY --from=frontend --chown=reviewer:reviewer /web/dist/ /app/frontend/dist/
USER reviewer
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health/live', timeout=3)"
CMD ["python", "-m", "uvicorn", "cash_review.app:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-access-log"]
