FROM pkms-base:latest
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY app.py .
EXPOSE 8002
USER 1000:1000
CMD ["python","app.py"]
