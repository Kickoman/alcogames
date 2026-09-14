FROM python:3.12-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
COPY frontend ./frontend

ENV PYTHONUNBUFFERED=1
ENV SERVICE_NAME=alcogames
ENV DATA_DIR=/app/data
ENV FRONTEND_DIR=/app/frontend

EXPOSE 8000

# --no-proxy-headers: uvicorn otherwise rewrites request.client from the
# forwarded headers when the peer is trusted, which erases the one address
# that is always true. The app records both itself, deliberately.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-proxy-headers"]
