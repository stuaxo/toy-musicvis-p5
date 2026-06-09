FROM python:3.11-slim-bookworm

# System packages: JVM (py5), audio, X11/OpenGL (py5 renderer), fonts, tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-client \
    openjdk-17-jdk \
    portaudio19-dev \
    libasound2-plugins \
    libsndfile1 \
    libgl1-mesa-dri \
    libgl1 \
    libegl1 \
    libglu1-mesa \
    libxi6 \
    libxtst6 \
    libxrender1 \
    fonts-dejavu \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set JAVA_HOME for py5 to use otherwise it will download the JVM itself
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV PATH="${JAVA_HOME}/bin:${PATH}"

RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && npm install -g @anthropic-ai/claude-code \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install uv; packages are installed from pyproject.toml via postCreateCommand
RUN pip install --no-cache-dir uv

ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=1000

RUN groupadd --gid ${USER_GID} ${USERNAME} \
    && useradd --uid ${USER_UID} --gid ${USER_GID} -m ${USERNAME} \
    && apt-get update \
    && apt-get install -y --no-install-recommends sudo \
    && echo "${USERNAME} ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/${USERNAME} \
    && chmod 0440 /etc/sudoers.d/${USERNAME} \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 109 render 2>/dev/null || true \
    && usermod -aG video,render,audio ${USERNAME}

USER ${USERNAME}

WORKDIR /workspace