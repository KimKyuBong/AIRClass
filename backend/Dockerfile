# AIRClass Backend Dockerfile
# FastAPI + LiveKit 통합 이미지
FROM python:3.13-slim

# uv 공식 이미지에서 바이너리 복사 (pip 대신)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    ffmpeg \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

# LiveKit Server 설치
ARG LIVEKIT_VERSION=1.9.11
RUN wget -q https://github.com/livekit/livekit/releases/download/v${LIVEKIT_VERSION}/livekit_${LIVEKIT_VERSION}_linux_amd64.tar.gz \
    && tar -xzf livekit_${LIVEKIT_VERSION}_linux_amd64.tar.gz \
    && mv livekit-server /usr/local/bin/ \
    && chmod +x /usr/local/bin/livekit-server \
    && rm livekit_${LIVEKIT_VERSION}_linux_amd64.tar.gz

# 작업 디렉토리 생성
WORKDIR /app

# Python 의존성 복사 및 uv로 설치
COPY requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt

# 애플리케이션 코드 복사
COPY config.py .
COPY main.py .
COPY core/ ./core/
COPY routers/ ./routers/
COPY services/ ./services/
COPY schemas/ ./schemas/
COPY utils/ ./utils/

# LiveKit 설정 디렉토리 생성
RUN mkdir -p /app/configs

# 포트 노출
# FastAPI: 8000
# LiveKit HTTP/WS: 7880-7910
# LiveKit RTC UDP: 50000-53020
EXPOSE 8000 7880-7910 50000-53020/udp

# 환경변수 기본값
ENV MODE=standalone \
    MAIN_NODE_URL="" \
    NODE_NAME=main \
    JWT_SECRET_KEY="" \
    MAX_CONNECTIONS=0 \
    LIVEKIT_BINARY=/usr/local/bin/livekit-server

# 헬스체크
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 시작 스크립트
COPY docker-entrypoint.sh /
RUN chmod +x /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]
