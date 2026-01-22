# AIRClass 개발 서버 실행 가이드

## 방법 1: 별도 터미널에서 실행 (권장)

### Terminal 1: Backend 서버
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

### Terminal 2: Frontend 서버
```bash
cd frontend
npm install
npm run dev
```

## 방법 2: 스크립트 사용 (개발 중)

```bash
# 서버 시작
./start-dev.sh

# 서버 상태 확인
./status.sh

# 서버 중지
./stop-dev.sh
```

## 접속 주소

- **Backend API**: http://localhost:8000
- **Frontend (교사)**: http://localhost:5173/#/teacher
- **Frontend (학생)**: http://localhost:5173/#/student  
- **Frontend (모니터)**: http://localhost:5173/#/monitor

## 문제 해결

### Backend가 시작되지 않을 때
```bash
cd backend
source venv/bin/activate
python main.py
```

### Frontend가 시작되지 않을 때
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run dev
```

### 포트가 이미 사용 중일 때
```bash
# 8000 포트 사용 중인 프로세스 확인
lsof -i :8000
kill -9 <PID>

# 5173 포트 사용 중인 프로세스 확인
lsof -i :5173
kill -9 <PID>
```
