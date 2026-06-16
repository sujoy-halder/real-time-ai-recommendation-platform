FROM apache/airflow:2.9.2-python3.11

USER root

# ==========================================
# INSTALL SYSTEM DEPENDENCIES
# ==========================================

RUN apt-get update && apt-get install -y \
    openjdk-17-jdk \
    curl \
    wget \
    gcc \
    g++ \
    procps \
    netcat-openbsd \
    build-essential \
    libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ==========================================
# JAVA CONFIG
# ==========================================

ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV PATH="${JAVA_HOME}/bin:${PATH}"

# ==========================================
# SWITCH TO AIRFLOW USER
# ==========================================

USER airflow

# ==========================================
# AIRFLOW / PYTHON CONFIG
# ==========================================

ENV AIRFLOW_VERSION=2.9.2
ENV PYTHON_VERSION=3.11
ENV CONSTRAINT_URL=https://raw.githubusercontent.com/apache/airflow/constraints-2.9.2/constraints-3.11.txt

# ==========================================
# UPGRADE PIP TO STABLE VERSION
# ==========================================

RUN pip install --no-cache-dir --upgrade \
    pip==24.0 \
    setuptools \
    wheel

# ==========================================
# INSTALL AIRFLOW PROVIDERS
# ==========================================

RUN pip install --no-cache-dir \
    --constraint "${CONSTRAINT_URL}" \
    apache-airflow-providers-apache-spark

# ==========================================
# INSTALL DATA / ML LIBRARIES
# ==========================================

RUN pip install --no-cache-dir \
    pyspark==3.5.1 \
    pandas==2.2.2 \
    numpy==1.26.4 \
    sqlalchemy==2.0.30 \
    psycopg2-binary==2.9.9 \
    kafka-python==2.0.2 \
    scikit-learn==1.5.0 \
    mlflow==2.13.0

# ==========================================
# SPARK CONFIG
# ==========================================

ENV SPARK_HOME=/home/airflow/.local/lib/python3.11/site-packages/pyspark
ENV PYSPARK_PYTHON=python3
ENV PYSPARK_DRIVER_PYTHON=python3

# ==========================================
# AIRFLOW HOME
# ==========================================

ENV AIRFLOW_HOME=/opt/airflow

WORKDIR /opt/airflow

# ==========================================
# VERIFY INSTALLATION
# ==========================================

RUN python --version && \
    pip --version && \
    java -version && \
    pyspark --version

# ==========================================
# DEFAULT COMMAND
# ==========================================

CMD ["airflow", "version"]