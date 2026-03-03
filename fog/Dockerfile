FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY fog_node.py .

CMD ["python", "-u", "fog_node.py"]
