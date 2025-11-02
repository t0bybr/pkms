FROM pkms-base:latest

# Set cache directory for Whisper models
ENV WHISPER_CACHE=/models
ENV XDG_CACHE_HOME=/models/.cache

COPY requirements.txt .
RUN pip install -r requirements.txt
COPY app.py .
EXPOSE 8004
USER 1000:1000
CMD ["python","app.py"]
