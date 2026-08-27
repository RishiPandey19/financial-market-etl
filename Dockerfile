FROM apache/airflow:2.10.5-python3.11

ARG AIRFLOW_VERSION=2.10.5
ARG PYTHON_VERSION=3.11

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt \
    --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PYTHON_VERSION}.txt"

ENV PYTHONPATH=/opt/airflow/project/src
