# Build from services/: docker build -f telegram-frontend/Dockerfile -t spbpu-telegram .
FROM python:3.11-slim

WORKDIR /app
ENV PYTHONPATH=/app
COPY telegram-frontend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY telegram-frontend/main.py .
COPY telegram-frontend/bot ./bot
COPY auth ./auth

EXPOSE 8090
CMD ["python", "main.py"]
