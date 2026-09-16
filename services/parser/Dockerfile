FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY config.py db.py ruz_client.py sync.py main.py email_utils.py telegram_utils.py notify.py .

EXPOSE 8082
CMD ["python", "main.py"]
