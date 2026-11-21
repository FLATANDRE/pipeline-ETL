ARG AIRFLOW_VERSION=3.3.2
FROM eclipse-temurin:17.0.17_10-jre-jammy AS java
FROM apache/airflow:${AIRFLOW_VERSION}-python3.11
ARG AIRFLOW_VERSION=3.3.2
ARG SPARK_VERSION=3.5.7
ARG ICEBERG_VERSION=1.10.0
USER root
COPY --from=java /opt/java/openjdk /opt/java/openjdk
ENV JAVA_HOME=/opt/java/openjdk
ENV PATH="/opt/java/openjdk/bin:${PATH}"
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN mkdir -p /opt/iceberg-jars /opt/lab-state /opt/airflow/generated /opt/airflow/logs \
    && chown -R airflow:0 /opt/iceberg-jars /opt/lab-state /opt/airflow/generated /opt/airflow/logs
RUN curl --fail --location --retry 3 -o /opt/iceberg-jars/iceberg-spark-runtime.jar \
    https://repo.maven.apache.org/maven2/org/apache/iceberg/iceberg-spark-runtime-3.5_2.12/${ICEBERG_VERSION}/iceberg-spark-runtime-3.5_2.12-${ICEBERG_VERSION}.jar \
    && echo '2ce6c02c8104a8ca2412a261abba7413964677db74ad96d25bd58e25abb7c27cbf94c7dc4cfa33eb12d05a2df04cb0074344983b09abbc43e4a1b4e4abf2b5e1  /opt/iceberg-jars/iceberg-spark-runtime.jar' | sha512sum -c - \
    && curl --fail --location --retry 3 -o /opt/iceberg-jars/iceberg-aws-bundle.jar \
    https://repo.maven.apache.org/maven2/org/apache/iceberg/iceberg-aws-bundle/${ICEBERG_VERSION}/iceberg-aws-bundle-${ICEBERG_VERSION}.jar \
    && echo '150b885dd827713af0b105e655ec24a47f823ce7269d218522b7149fdb1606039458470e5006da31c9fdc5bb839c59447279e7968e04bd6d7984c57d46980ccb  /opt/iceberg-jars/iceberg-aws-bundle.jar' | sha512sum -c -
USER airflow
RUN pip install --no-cache-dir "apache-airflow==${AIRFLOW_VERSION}" \
    "pyspark==${SPARK_VERSION}" "boto3==1.40.74" "requests==2.32.5" "pytest==8.3.5" \
    "apache-airflow-providers-standard==1.19.0" "psycopg2-binary==2.9.11" "PyYAML==6.0.3"
ENV PYTHONPATH=/opt/lab
ENV PYSPARK_PYTHON=python
ENV SPARK_LOCAL_IP=127.0.0.1
WORKDIR /opt/lab
