FROM pkms-base:latest

# Set cache directories before any imports
ENV HF_HOME=/models/huggingface
ENV TRANSFORMERS_CACHE=/models/huggingface
ENV TORCH_HOME=/models/torch

COPY requirements.txt .
RUN pip install -r requirements.txt
COPY app.py .
EXPOSE 8003
USER 1000:1000
CMD ["python","app.py"]
