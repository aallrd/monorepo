FROM maven:3.9.16-eclipse-temurin-21

USER root

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
      bash \
      ca-certificates \
      git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workdir
