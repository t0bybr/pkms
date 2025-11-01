FROM python:3.11-slim
RUN apt-get update && apt-get install -y libgl1 git && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
EXPOSE 8001
USER 1000:1000
CMD ["python","app.py"]
