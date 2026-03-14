FROM python:3.11-slim-bookworm

ARG RTLSDR_GIT_REF=master
ARG PYRTLSDR_VERSION=0.3.0

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Include minimal runtime + build tooling for arm wheel fallback and librtlsdr.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        cmake \
        gfortran \
        git \
        binutils \
        pkg-config \
        libopenblas-dev \
        libusb-1.0-0 \
        libusb-1.0-0-dev \
        ca-certificates \
        curl \
    && git clone --branch "${RTLSDR_GIT_REF}" --depth 1 https://github.com/osmocom/rtl-sdr.git /tmp/rtl-sdr \
    && cmake -S /tmp/rtl-sdr -B /tmp/rtl-sdr/build -DDETACH_KERNEL_DRIVER=ON \
    && cmake --build /tmp/rtl-sdr/build --parallel "$(nproc)" \
    && cmake --install /tmp/rtl-sdr/build \
    && ldconfig \
    && nm -D /usr/local/lib/librtlsdr.so | grep -q 'rtlsdr_set_center_freq' \
    && ! nm -D /usr/local/lib/librtlsdr.so | grep -q 'rtlsdr_set_dithering' \
    && rm -rf /tmp/rtl-sdr \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md /app/
COPY src /app/src

RUN pip install --upgrade pip \
    && pip install "pyrtlsdr==${PYRTLSDR_VERSION}" \
    && pip install . \
    && python -c "import importlib.metadata as m; import rtlsdr; assert m.version('pyrtlsdr') == '${PYRTLSDR_VERSION}'; print(rtlsdr.__file__)"

RUN groupadd -f plugdev && useradd --create-home --shell /usr/sbin/nologin rfpr

RUN mkdir -p /config /data && chown -R rfpr:rfpr /config /data /app

USER rfpr

EXPOSE 8787

ENTRYPOINT ["rfpr"]
CMD ["run", "--config", "/config/settings.yaml"]
