FROM python:3.11-slim

WORKDIR /opt/lab
COPY dashboard/requirements.txt /opt/lab/dashboard/requirements.txt
RUN pip install --no-cache-dir -r dashboard/requirements.txt
COPY app/__init__.py app/trino_client.py /opt/lab/app/
COPY dashboard/dashboard.py /opt/lab/dashboard/dashboard.py
ENV PYTHONPATH=/opt/lab
EXPOSE 8501
CMD ["streamlit", "run", "dashboard/dashboard.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]
