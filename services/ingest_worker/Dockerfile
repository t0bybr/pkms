FROM pkms-base:latest
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 9000
USER 1000:1000
CMD ["python","worker.py"]

