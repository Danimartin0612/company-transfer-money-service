FROM jenkins/jenkins:lts-jdk21

USER root

RUN apt-get update && apt-get install -y \
    curl ca-certificates gnupg lsb-release \
 && install -m 0755 -d /etc/apt/keyrings \
 && curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg \
 && chmod a+r /etc/apt/keyrings/docker.gpg \
 && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian bookworm stable" \
      > /etc/apt/sources.list.d/docker.list \
 && apt-get update \
 && apt-get install -y docker-ce-cli git \
 && rm -rf /var/lib/apt/lists/*

ARG PY_VER=3.12.7

# Dependencias de compilación
RUN apt-get update && apt-get install -y \
    build-essential wget xz-utils \
    libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev \
    libffi-dev libncursesw5-dev liblzma-dev tk-dev uuid-dev \
 && rm -rf /var/lib/apt/lists/*

# Descargar, compilar e instalar con altinstall para no pisa /usr/bin/python3
RUN --mount=type=cache,target=/root/.cache/wget \
    cd /tmp \
 && wget -q https://www.python.org/ftp/python/${PY_VER}/Python-${PY_VER}.tar.xz \
 && tar -xf Python-${PY_VER}.tar.xz \
 && cd Python-${PY_VER} \
 && ./configure --with-ensurepip=install \
 && make -s -j"$(nproc)" \
 && make altinstall \
 && /usr/local/bin/python3.12 -m pip install --upgrade pip \
 && rm -rf /tmp/Python-${PY_VER} /tmp/Python-${PY_VER}.tar.xz

RUN /usr/local/bin/python3.12 -m venv /opt/py312 \
 && /opt/py312/bin/python -m pip install --upgrade pip

ENV PATH="/opt/py312/bin:${PATH}"

USER jenkins
