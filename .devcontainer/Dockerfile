FROM python:3.13-slim-bookworm

# ---------------------------------------------------------------
# System packages
# ---------------------------------------------------------------
# java-17           — required by py5's JVM
# portaudio19-dev   — required by sounddevice (PortAudio bindings)
# libsndfile1       — pulled in by soundfile if used later
# x11-apps          — provides xauth; needed for X11 forwarding
# libgl1            — OpenGL; py5's JAVA2D renderer needs it
# libxi6 libxtst6   — input/accessibility libs the JVM wants
# fonts-dejavu      — py5 needs at least one font family available
# git & curl        — required for version control and fetching Node
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

# Point py5 at the system JDK so it doesn't try to download its own
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV PATH="${JAVA_HOME}/bin:${PATH}"

# ---------------------------------------------------------------
# Node.js & Claude Code CLI
# ---------------------------------------------------------------
# Claude Code requires Node 18+. We use the official NodeSource 
# script to install Node 20 LTS, then install the CLI globally.
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && npm install -g @anthropic-ai/claude-code \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------------
# Python dependencies
# ---------------------------------------------------------------
RUN pip install --no-cache-dir \
    py5 \
    sounddevice \
    numpy

# ---------------------------------------------------------------
# Non-root user
# ---------------------------------------------------------------
# "vscode" is the conventional devcontainer username; Claude Code
# and VS Code both recognise it and drop privileges automatically.
# UID 1000 matches the typical first user on Ubuntu, which matters
# for the X11 and PulseAudio socket mounts.
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

# ---------------------------------------------------------------
# Working directory — project files are volume-mounted here
# ---------------------------------------------------------------
WORKDIR /workspace