FROM python:3.11-slim
RUN apt-get update && apt-get install -y poppler-utils tesseract-ocr libgl1 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 9000
USER 1000:1000
CMD ["python","worker.py"]

