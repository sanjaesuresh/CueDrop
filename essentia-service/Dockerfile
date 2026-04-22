FROM python:3.10-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libfftw3-dev \
    libyaml-dev \
    libavcodec-dev \
    libavformat-dev \
    libavutil-dev \
    libswresample-dev \
    libsamplerate0-dev \
    libtag1-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    essentia \
    essentia-tensorflow \
    fastapi \
    uvicorn[standard] \
    python-multipart \
    numpy

COPY server.py /app/server.py
WORKDIR /app

EXPOSE 8001
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001"]
