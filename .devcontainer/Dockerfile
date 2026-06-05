FROM python:3.13-slim-bookworm

# System packages: JVM (py5), audio, X11/OpenGL (py5 renderer), fonts, tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    openjdk-17-jdk \
    portaudio19-dev \
    libsndfile1 \
    x11-apps \
    libgl1 \
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

RUN pip install --no-cache-dir \
    py5 \
    sounddevice \
    numpy

ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=1000

RUN groupadd --gid ${USER_GID} ${USERNAME} \
    && useradd --uid ${USER_UID} --gid ${USER_GID} -m ${USERNAME} \
    && apt-get update \
    && apt-get install -y --no-install-recommends sudo \
    && echo "${USERNAME} ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/${USERNAME} \
    && chmod 0440 /etc/sudoers.d/${USERNAME} \
    && rm -rf /var/lib/apt/lists/*

USER ${USERNAME}

WORKDIR /workspace