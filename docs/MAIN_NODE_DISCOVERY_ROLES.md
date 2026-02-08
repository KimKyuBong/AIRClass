# 메인 노드 발견·연결 역할 정리

"메인 노드를 발견하고 연결하는 것"을 **누구의 역할로 둘지**에 대한 정리입니다.

---

## 1. 현재 구조 요약

| 주체 | 역할 | 구현 위치 |
|------|------|-----------|
| **Main 노드** | 자신을 **광고** (발견당하는 쪽) | `cluster.py` → mDNS `advertise_main_node()` |
| **Sub 노드** | 메인을 **발견**(mDNS 등) 후 **자신을 등록·연결** (인증: CLUSTER_SECRET 또는 TOTP device 토큰) | `cluster.py` + `core/discovery.py` → `find_main_node_with_fallback()` |
| **프론트(Teacher/Student)** | 고정된 API/WS URL로 통신 (발견 없음) | `VITE_BACKEND_URL` / 현재 호스트 |
| **GUI 매니저** | `.env`에 SERVER_IP 등 설정 (발견 없음) | `gui/airclass_gui.py` |

---

## 2. 역할 배치 권장안

### 2.1 메인을 **발견하고 연결하는 주체 → Sub 노드** (유지 권장)

- **이유**
  - Sub가 **자기가 붙을 상대(메인)**를 찾는 것이 자연스러움.
  - 메인은 “광고만”, Sub는 “발견 + 연결”로 책임이 명확함.
  - 이미 `MAIN_NODE_URL` 없을 때 `find_main_node_with_fallback()`으로 구현되어 있음.
- **정리**: **“메인 노드를 발견하고 연결하는 것”은 Sub의 역할로 두는 것이 좋다.**

### 2.2 메인 노드 → 발견당하는 쪽 (광고만)

- **역할**: 자신을 mDNS 등으로 **광고**해서 Sub가 찾을 수 있게 함.
- **연결 책임**: 없음. Sub가 찾아서 연결함.
- **현재**: `advertise_main_node()`로 잘 분리되어 있음.

### 2.3 프론트(Teacher/Student) → discovery 역할 두지 않기

- **이유**
  - 브라우저가 여러 후보를 스캔하면 CORS·보안·구현 복잡도가 커짐.
  - 일반적으로 “하나의 진입점(API 서버/로드밸런서)”만 쓰는 구성이 맞음.
  - 그 진입점이 메인일 수도, 메인 앞단 프록시일 수도 있음.
- **정리**: 프론트는 **메인 발견·연결 역할을 두지 않고**,  
  **하나의 API/WS URL(환경 설정 또는 현재 호스트)만 사용하는 것이 좋다.**

### 2.4 GUI 매니저 → 선택적 “편의 기능”만

- **가능한 역할**: “자동으로 메인(또는 서버) 찾기” 버튼으로 discovery를 한 번 돌려,  
  `.env`의 `SERVER_IP` 등을 채워 넣는 **편의 기능**.
- **정리**: **주된 책임은 Sub에 두고**, GUI는 “사용자 편의용 자동 채우기” 정도로만 두는 것이 좋다.

---

## 3. 요약

| 질문 | 권장 답 |
|------|--------|
| 메인을 **발견**하는 주체는? | **Sub 노드** (이미 구현됨). |
| 메인을 **연결**하는 주체는? | **Sub 노드** (발견 후 자기 자신을 메인에 등록·연결). |
| Main 노드 역할은? | **광고** (mDNS 등). 연결은 하지 않음. |
| 프론트가 메인을 발견해야 할까? | **아니오.** 하나의 URL만 쓰는 구성이 좋음. |
| GUI가 메인 발견할까? | **선택.** 편의용 “자동 찾기”만 두고, 주된 책임은 Sub에 둠. |

이렇게 두면 “메인 노드 발견·연결”의 **단일 책임**은 Sub에 있고, 나머지는 각자 역할이 명확해집니다.

---

## 4. 인증: Sub ↔ Main

- **방식 1 (기존)**: `CLUSTER_SECRET` 공유 → HMAC(auth_token + timestamp)로 등록·통계·해제.
- **방식 2 (Android와 동일)**: Sub에 `TOTP_SECRET` 설정 → 메인과 동일한 TOTP로 **device 토큰** 발급(`POST /api/auth/device-token`) 후, Bearer 토큰으로 등록·통계·해제. `MAIN_NODE_URL` 없으면 **mDNS**로 메인 발견 후 위와 동일하게 인증.

## 5. 보안: "아무 노드나 붙으면 안 된다"

- **Main이 Sub를 받을 때**: **CLUSTER_SECRET**(HMAC) 또는 **Bearer device 토큰**(TOTP 발급)으로 검증. 시크릿/토큰을 모르는 노드는 등록·통계 불가.
- **Sub가 Main을 찾을 때**: 발견 단계에서는 **Main 정체성 검증이 없음**. 가짜 Main에 붙거나 시크릿 유출 위험 가능.
- **Unregister**: Bearer 또는 HMAC(auth_token+timestamp)로 인증 후 해제 가능.

자세한 위험 요소와 권장 보완(타임스탬프 유효 구간, Main 정체성 검증 등)은 **docs/SECURITY_CLUSTER.md**를 참고하세요.

---

## 6. Sub 노드 설정 예

- **같은 Docker Compose**: `MAIN_NODE_URL: http://main:8000`, `CLUSTER_SECRET` 또는 `TOTP_SECRET` 중 하나 설정.
- **다른 호스트(다른 PC 등)**: `MAIN_NODE_URL` 비우고 `TOTP_SECRET`만 설정하면 **mDNS**로 메인 발견 후 **device 토큰**으로 등록 (Android 앱과 동일한 흐름).
