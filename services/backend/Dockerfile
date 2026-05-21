FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY db.py auth_utils.py app.py main.py ./

EXPOSE 8083
CMD ["python", "main.py"]
