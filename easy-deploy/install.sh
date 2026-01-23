#!/bin/bash
#
# AIRClass 원클릭 설치 스크립트
# 교사들이 쉽게 멀티 컴퓨터 스트리밍 클러스터를 구축할 수 있도록 도와줍니다
#
# 사용법:
#   curl -sSL https://airclass.example.com/install.sh | bash
#   또는
#   ./install.sh
#

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 헬퍼 함수
print_header() {
    echo -e "${PURPLE}"
    echo "╔══════════════════════════════════════════════╗"
    echo "║     🎓 AIRClass 클러스터 설치 마법사         ║"
    echo "╚══════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_step() {
    echo -e "${CYAN}▶ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# 네트워크 IP 가져오기
get_local_ip() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "localhost"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        hostname -I | awk '{print $1}' || ip route get 1 | awk '{print $7}' || echo "localhost"
    else
        echo "localhost"
    fi
}

# Docker 확인
check_docker() {
    print_step "Docker 설치 확인 중..."
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker가 설치되지 않았습니다"
        echo ""
        print_info "Docker Desktop을 설치해주세요:"
        echo ""
        
        if [[ "$OSTYPE" == "darwin"* ]]; then
            echo "  🍎 macOS: https://www.docker.com/products/docker-desktop/"
            read -p "브라우저로 다운로드 페이지를 여시겠습니까? (y/n) " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                open "https://www.docker.com/products/docker-desktop/"
            fi
        elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
            echo "  🐧 Linux: https://docs.docker.com/engine/install/"
            read -p "브라우저로 설치 가이드를 여시겠습니까? (y/n) " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                xdg-open "https://docs.docker.com/engine/install/" 2>/dev/null || true
            fi
        fi
        
        echo ""
        print_warning "Docker 설치 후 다시 실행해주세요"
        exit 1
    fi
    
    # Docker 실행 확인
    if ! docker ps &> /dev/null; then
        print_error "Docker가 실행 중이 아닙니다"
        print_info "Docker Desktop을 실행한 후 다시 시도해주세요"
        exit 1
    fi
    
    print_success "Docker 확인 완료"
}

# 역할 선택
select_role() {
    echo ""
    echo -e "${PURPLE}╔══════════════════════════════════════════════╗${NC}"
    echo -e "${PURPLE}║  이 컴퓨터의 역할을 선택해주세요:             ║${NC}"
    echo -e "${PURPLE}╚══════════════════════════════════════════════╝${NC}"
    echo ""
    echo "  1) 🎯 메인 노드 (Main Node)"
    echo "     - 첫 번째 컴퓨터 (관리용)"
    echo "     - 다른 컴퓨터들을 관리하고 부하를 분산합니다"
    echo "     - 웹 대시보드를 제공합니다"
    echo ""
    echo "  2) 🖥️  서브 노드 (Sub Node)"
    echo "     - 추가 컴퓨터 (용량 증설용)"
    echo "     - 메인 노드에 연결되어 스트리밍을 처리합니다"
    echo "     - 150명의 학생을 추가로 수용할 수 있습니다"
    echo ""
    
    while true; do
        read -p "선택 (1 또는 2): " role_choice
        case $role_choice in
            1)
                ROLE="main"
                print_success "메인 노드로 설치합니다"
                break
                ;;
            2)
                ROLE="sub"
                print_success "서브 노드로 설치합니다"
                break
                ;;
            *)
                print_warning "1 또는 2를 입력해주세요"
                ;;
        esac
    done
}

# 프로젝트 다운로드
download_project() {
    print_step "AIRClass 프로젝트 다운로드 중..."
    
    # 설치 디렉토리
    INSTALL_DIR="$HOME/AirClass"
    
    if [ -d "$INSTALL_DIR" ]; then
        print_warning "기존 설치가 발견되었습니다: $INSTALL_DIR"
        read -p "기존 설치를 덮어쓰시겠습니까? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_info "설치를 취소합니다"
            exit 0
        fi
        rm -rf "$INSTALL_DIR"
    fi
    
    # Git이 있으면 clone, 없으면 스킵 (이미 디렉토리에 있다고 가정)
    if command -v git &> /dev/null; then
        print_info "Git을 사용하여 다운로드합니다..."
        git clone https://github.com/your-repo/AirClass.git "$INSTALL_DIR" 2>/dev/null || {
            print_warning "Git clone 실패, 현재 디렉토리를 사용합니다"
            INSTALL_DIR="$(pwd)"
        }
    else
        print_warning "Git이 설치되지 않았습니다. 현재 디렉토리를 사용합니다"
        INSTALL_DIR="$(pwd)"
    fi
    
    cd "$INSTALL_DIR"
    print_success "프로젝트 준비 완료: $INSTALL_DIR"
}

# 메인 노드 설치
install_main_node() {
    print_step "메인 노드를 설정합니다..."
    
    # Docker Compose로 메인 노드만 실행
    docker compose up -d main
    
    # 서비스 시작 대기
    print_step "서비스 시작을 기다리는 중..."
    sleep 10
    
    # 헬스 체크
    for i in {1..30}; do
        if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
            print_success "메인 노드가 성공적으로 시작되었습니다!"
            break
        fi
        echo -n "."
        sleep 2
    done
    echo ""
    
    # 로컬 IP 주소
    LOCAL_IP=$(get_local_ip)
    
    # 성공 메시지
    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║     🎉 메인 노드 설치 완료!                  ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${CYAN}📊 관리 대시보드:${NC}"
    echo "   http://localhost:3000"
    echo "   http://$LOCAL_IP:3000 (다른 기기에서)"
    echo ""
    echo -e "${CYAN}📋 서브 노드 추가 방법:${NC}"
    echo "   다른 컴퓨터에서 다음 명령을 실행하세요:"
    echo ""
    echo -e "${YELLOW}   curl -sSL http://$LOCAL_IP:3000/install.sh | bash${NC}"
    echo ""
    echo "   또는 대시보드에서 QR 코드를 스캔하세요"
    echo ""
    echo -e "${CYAN}🎬 Android 앱 연결:${NC}"
    echo "   RTMP URL: rtmp://$LOCAL_IP:1935/live/stream"
    echo ""
    
    # 브라우저 자동 열기
    print_step "대시보드를 여는 중..."
    sleep 2
    if [[ "$OSTYPE" == "darwin"* ]]; then
        open "http://localhost:3000" 2>/dev/null || true
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        xdg-open "http://localhost:3000" 2>/dev/null || true
    fi
}

# 메인 노드 자동 발견 (다중 전략)
auto_discover_main_node() {
    print_step "🔍 메인 노드 자동 발견 중..."
    echo ""
    
    # 전략 1: mDNS (Bonjour/Avahi)
    print_info "전략 1/4: mDNS 브로드캐스트 검색 (3초)..."
    if command -v avahi-browse &> /dev/null; then
        # Linux - Avahi
        MAIN_IP=$(timeout 3 avahi-browse -t -r _airclass._tcp 2>/dev/null | grep "address" | head -1 | awk '{print $3}' || echo "")
    elif command -v dns-sd &> /dev/null; then
        # macOS - dns-sd
        MAIN_IP=$(timeout 3 dns-sd -B _airclass._tcp 2>/dev/null | grep "airclass" | head -1 | awk '{print $7}' || echo "")
    fi
    
    if [ -n "$MAIN_IP" ] && [ "$MAIN_IP" != "" ]; then
        print_success "✅ mDNS로 발견: $MAIN_IP"
        return 0
    fi
    print_warning "❌ mDNS 실패 (학교 네트워크에서 차단되었을 수 있습니다)"
    
    # 전략 2: 로컬 네트워크 스캔
    print_info "전략 2/4: 로컬 네트워크 스캔 (5초)..."
    LOCAL_NETWORK=$(ip route 2>/dev/null | grep "src" | head -1 | awk '{print $1}' || \
                    netstat -rn 2>/dev/null | grep "default" | head -1 | awk '{print $2}' || echo "")
    
    if [ -n "$LOCAL_NETWORK" ]; then
        # 네트워크 프리픽스 추출 (예: 192.168.1)
        NETWORK_PREFIX=$(echo "$LOCAL_NETWORK" | cut -d'.' -f1-3)
        
        # 일반적인 IP들 먼저 확인 (빠른 발견)
        for ip_suffix in 1 100 101 254; do
            test_ip="${NETWORK_PREFIX}.${ip_suffix}"
            if curl -sf --max-time 1 "http://$test_ip:8000/health" > /dev/null 2>&1; then
                response=$(curl -s "http://$test_ip:8000/health")
                if echo "$response" | grep -q '"mode":"main"' || echo "$response" | grep -q '"status":"healthy"'; then
                    MAIN_IP="$test_ip"
                    print_success "✅ 네트워크 스캔으로 발견: $MAIN_IP"
                    return 0
                fi
            fi
        done
    fi
    print_warning "❌ 네트워크 스캔 실패"
    
    # 전략 3: 게이트웨이 확인
    print_info "전략 3/4: 기본 게이트웨이 확인..."
    GATEWAY=$(ip route 2>/dev/null | grep default | awk '{print $3}' || \
              netstat -rn 2>/dev/null | grep default | head -1 | awk '{print $2}' || echo "")
    
    if [ -n "$GATEWAY" ] && [ "$GATEWAY" != "0.0.0.0" ]; then
        if curl -sf --max-time 2 "http://$GATEWAY:8000/health" > /dev/null 2>&1; then
            MAIN_IP="$GATEWAY"
            print_success "✅ 게이트웨이에서 발견: $MAIN_IP"
            return 0
        fi
    fi
    print_warning "❌ 게이트웨이 확인 실패"
    
    # 전략 4: 수동 입력
    print_info "전략 4/4: 수동 입력 필요"
    echo ""
    print_warning "자동 발견에 실패했습니다"
    print_info "메인 노드 대시보드에 표시된 IP 주소를 입력해주세요"
    echo ""
    
    return 1
}

# 서브 노드 설치
install_sub_node() {
    print_step "서브 노드를 설정합니다..."
    echo ""
    
    # 자동 발견 시도
    if auto_discover_main_node; then
        # 자동 발견 성공
        print_step "발견된 메인 노드 확인 중: $MAIN_IP"
        
        # 한 번 더 검증
        if ! curl -sf "http://$MAIN_IP:8000/health" > /dev/null 2>&1; then
            print_error "메인 노드 응답 없음, 수동 입력으로 전환합니다"
            MAIN_IP=""
        fi
    fi
    
    # 자동 발견 실패 시 수동 입력
    while [ -z "$MAIN_IP" ]; do
        read -p "메인 노드 IP 주소를 입력하세요: " MAIN_IP
        
        if [ -z "$MAIN_IP" ]; then
            print_warning "IP 주소를 입력해주세요"
            continue
        fi
        
        # 메인 노드 연결 테스트
        print_step "메인 노드 연결 테스트 중..."
        if curl -sf --max-time 3 "http://$MAIN_IP:8000/health" > /dev/null 2>&1; then
            print_success "✅ 메인 노드 연결 성공!"
            break
        else
            print_error "❌ 메인 노드에 연결할 수 없습니다"
            print_info "IP 주소를 확인하거나, 메인 노드가 실행 중인지 확인해주세요"
            echo ""
            print_info "일반적인 확인 사항:"
            echo "  1. 메인 노드가 실행 중인가요?"
            echo "  2. 같은 네트워크에 연결되어 있나요?"
            echo "  3. 방화벽이 포트 8000을 차단하고 있나요?"
            echo ""
            read -p "다시 시도하시겠습니까? (y/n) " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                exit 1
            fi
            MAIN_IP=""  # 다시 입력받기
        fi
    done
    
    # 환경 변수 설정
    export MAIN_NODE_URL="http://$MAIN_IP:8000"
    
    # 서브 노드 실행
    docker compose up -d sub
    
    # 서비스 시작 대기
    print_step "서비스 시작을 기다리는 중..."
    sleep 10
    
    # 성공 메시지
    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║     🎉 서브 노드 설치 완료!                  ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${CYAN}✅ 메인 노드에 자동 등록되었습니다${NC}"
    echo ""
    echo "📊 클러스터 상태를 확인하려면 대시보드를 방문하세요:"
    echo "   http://$MAIN_IP:3000"
    echo ""
    echo "💡 이 컴퓨터는 이제 최대 150명의 학생을 추가로 수용할 수 있습니다"
    echo ""
}

# 메인 함수
main() {
    print_header
    
    # 1. Docker 확인
    check_docker
    
    # 2. 역할 선택
    select_role
    
    # 3. 프로젝트 다운로드
    download_project
    
    # 4. 역할에 따라 설치
    if [ "$ROLE" == "main" ]; then
        install_main_node
    else
        install_sub_node
    fi
    
    echo ""
    print_success "모든 설정이 완료되었습니다!"
    echo ""
}

# 스크립트 실행
main
