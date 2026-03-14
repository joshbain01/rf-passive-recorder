FROM python:3.11-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Include minimal runtime + conservative build tooling for arm wheel fallback.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        gfortran \
        pkg-config \
        libopenblas-dev \
        librtlsdr0 \
        librtlsdr-dev \
        libusb-1.0-0 \
        libusb-1.0-0-dev \
        ca-certificates \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md /app/
COPY src /app/src

RUN pip install --upgrade pip \
    && pip install .

RUN groupadd -f plugdev && useradd --create-home --shell /usr/sbin/nologin rfpr

RUN mkdir -p /config /data && chown -R rfpr:rfpr /config /data /app

USER rfpr

EXPOSE 8787

ENTRYPOINT ["rfpr"]
CMD ["run", "--config", "/config/settings.yaml"]
