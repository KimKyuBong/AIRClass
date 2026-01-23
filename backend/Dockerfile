# AIRClass Backend Dockerfile
FROM python:3.11-slim

# 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    ffmpeg \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

# 작업 디렉토리 생성
WORKDIR /app

# Python 의존성 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# MediaMTX 다운로드 (ARM/x86 자동 감지)
ARG TARGETARCH
RUN ARCH=$([ "$TARGETARCH" = "arm64" ] && echo "arm64v8" || echo "amd64") && \
    wget https://github.com/bluenviron/mediamtx/releases/download/v1.9.3/mediamtx_v1.9.3_linux_${ARCH}.tar.gz && \
    tar -xzf mediamtx_v1.9.3_linux_${ARCH}.tar.gz && \
    rm mediamtx_v1.9.3_linux_${ARCH}.tar.gz && \
    chmod +x mediamtx

# 애플리케이션 코드 복사
COPY config.py .
COPY main.py .
COPY mediamtx.yml .
COPY mediamtx-main.yml .
COPY cluster.py .
COPY discovery.py .

# 포트 노출
EXPOSE 8000 1935 8888

# 환경변수 기본값
ENV MODE=sub \
    MAIN_NODE_URL="" \
    NODE_NAME=sub \
    JWT_SECRET_KEY="" \
    MAX_CONNECTIONS=150

# 헬스체크
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 시작 스크립트
COPY docker-entrypoint.sh /
RUN chmod +x /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]
