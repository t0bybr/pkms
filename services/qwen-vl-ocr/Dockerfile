FROM pkms-base:latest

# Set cache directories before any imports
ENV HF_HOME=/models/huggingface
ENV TRANSFORMERS_CACHE=/models/huggingface

COPY requirements.txt .
RUN pip install -r requirements.txt
COPY app.py .
EXPOSE 8001
USER 1000:1000
CMD ["python","app.py"]
