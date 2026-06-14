# Build from services/: docker build -f backend/Dockerfile -t spbpu-backend .
FROM python:3.11-slim

WORKDIR /app
ENV PYTHONPATH=/app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/db.py backend/auth_utils.py backend/captcha_utils.py backend/app.py backend/main.py ./
COPY auth ./auth

EXPOSE 8083
CMD ["python", "main.py"]
