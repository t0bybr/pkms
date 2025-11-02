FROM pkms-base:latest
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
# create writable mountpoint for cache (used when container root is read-only)
RUN mkdir -p /app/cache && chown -R 1000:1000 /app/cache
EXPOSE 8080
USER 1000:1000
CMD ["python","app.py"]
