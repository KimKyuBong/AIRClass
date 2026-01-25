#!/bin/bash

export LANG=ko_KR.UTF-8

echo "========================================"
echo "  AIRClass 초기 설정 마법사"
echo "========================================"
echo ""

# 기존 .env 파일이 있으면 백업
if [ -f ".env" ]; then
    echo "기존 설정 파일을 발견했습니다."
    echo "백업 파일을 생성합니다: .env.backup"
    cp .env .env.backup
    echo ""
fi

echo "1. 서버 IP 주소 자동 감지 중..."
echo ""

# 자동으로 IP 주소 감지
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    DETECTED_IPS=$(ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}')
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    DETECTED_IPS=$(hostname -I | tr ' ' '\n' | grep -v 127.0.0.1)
else
    # Windows WSL or other
    DETECTED_IPS=$(ip addr show | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}' | cut -d'/' -f1)
fi

# IP 목록 출력
echo "감지된 IP 주소:"
IFS=$'\n'
IP_ARRAY=($DETECTED_IPS)
unset IFS

if [ ${#IP_ARRAY[@]} -eq 0 ]; then
    echo "   (감지된 IP가 없습니다)"
    DEFAULT_IP="localhost"
elif [ ${#IP_ARRAY[@]} -eq 1 ]; then
    DEFAULT_IP="${IP_ARRAY[0]}"
    echo "   1) $DEFAULT_IP (자동 선택됨)"
else
    for i in "${!IP_ARRAY[@]}"; do
        echo "   $((i+1))) ${IP_ARRAY[$i]}"
    done
    DEFAULT_IP="${IP_ARRAY[0]}"
fi

echo ""
echo "   학생들이 접속할 IP 주소를 선택하세요"
echo "   (일반적으로 Wi-Fi 또는 유선 랜 IP)"
echo ""
read -p "서버 IP 주소 [기본값: $DEFAULT_IP]: " SERVER_IP

if [ -z "$SERVER_IP" ]; then
    SERVER_IP="$DEFAULT_IP"
    echo "기본값 사용: $SERVER_IP"
fi

echo ""
echo "2. 클래스 비밀번호를 입력하세요"
echo "   (다른 선생님의 서버와 구분하기 위한 암호)"
echo "   예: math2025, room303, myclass 등"
echo ""
read -p "클래스 비밀번호: " CLUSTER_SECRET

if [ -z "$CLUSTER_SECRET" ]; then
    echo "[경고] 비밀번호를 입력하지 않았습니다. 기본값을 사용합니다."
    CLUSTER_SECRET="airclass2025"
fi

echo ""
echo "3. JWT 암호화 키를 생성합니다..."
echo "   (자동 생성됩니다)"
echo ""

# JWT_SECRET_KEY 랜덤 생성
if command -v openssl &> /dev/null; then
    JWT_SECRET_KEY=$(openssl rand -hex 32)
elif command -v uuidgen &> /dev/null; then
    JWT_SECRET_KEY="$(uuidgen)$(uuidgen)" | tr -d '-'
else
    # Fallback: /dev/urandom 사용
    JWT_SECRET_KEY=$(cat /dev/urandom | LC_ALL=C tr -dc 'a-zA-Z0-9' | fold -w 64 | head -n 1)
fi

echo "========================================"
echo "  설정 내용 확인"
echo "========================================"
echo ""
echo "서버 IP 주소:      $SERVER_IP"
echo "클래스 비밀번호:   $CLUSTER_SECRET"
echo "JWT 암호화 키:     $JWT_SECRET_KEY"
echo ""
echo "========================================"
echo ""

read -p "이 설정으로 진행하시겠습니까? (y/N): " CONFIRM

if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
    echo "설정을 취소했습니다."
    echo "./setup.sh를 다시 실행해주세요."
    exit 1
fi

echo ""
echo ".env 파일 생성 중..."

cat > .env << EOF
# AIRClass 서버 설정 파일
# 생성일: $(date)

# 서버 IP 주소 (학생들이 접속할 주소)
SERVER_IP=$SERVER_IP

# 프론트엔드 백엔드 URL
VITE_BACKEND_URL=http://$SERVER_IP:8000

# CORS 설정 (* = 모든 도메인 허용)
CORS_ORIGINS=*

# JWT 보안 키 (자동 생성)
JWT_SECRET_KEY=$JWT_SECRET_KEY

# Main 노드 WebRTC 사용 여부 (false = Sub 노드로 부하분산)
USE_MAIN_WEBRTC=false

# 클러스터 보안: Main과 Sub 노드가 서로를 인증하는 비밀번호
# 다른 선생님의 서버와 구분하기 위해 사용됩니다
CLUSTER_SECRET=$CLUSTER_SECRET
EOF

echo ""
echo "========================================"
echo "  설정이 완료되었습니다!"
echo "========================================"
echo ""
echo "다음 단계:"
echo "  1. ./start.sh를 실행하여 서버를 시작하세요"
echo "  2. 브라우저에서 http://$SERVER_IP:5173/teacher 접속"
echo "  3. 학생들에게 http://$SERVER_IP:5173/student 주소 공유"
echo ""
echo "설정 변경: ./setup.sh 다시 실행"
echo "서버 시작: ./start.sh 실행"
echo ""
