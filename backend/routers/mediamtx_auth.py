"""
MediaMTX Authentication Router
==============================
MediaMTX HTTP 인증 콜백 엔드포인트

MediaMTX가 클라이언트 인증 시 호출하는 엔드포인트
프로토콜별 접근 제어:
- RTMP publish: Android 앱의 스트리밍 (항상 허용)
- WebRTC publish: 교사 화면 공유 (JWT 인증 + 교사 권한)
- RTMP read: 내부 프록시만 허용 (localhost)
- RTSP read: FFmpeg 프록시 허용
- WebRTC read: JWT 토큰 인증 필요
"""

import logging
from fastapi import APIRouter, HTTPException
from utils import verify_token

logger = logging.getLogger("uvicorn")
router = APIRouter(prefix="/api/auth", tags=["mediamtx"])


@router.post("/mediamtx")
async def mediamtx_auth(request: dict):
    """
    MediaMTX HTTP 인증 엔드포인트

    MediaMTX가 클라이언트 인증 시 호출
    """
    action = request.get("action")
    path = request.get("path")
    query = request.get("query", "")
    protocol = request.get("protocol")
    ip = request.get("ip", "")

    # 디버깅용 로그
    print(
        f"[MediaMTX Auth] action={action}, protocol={protocol}, path={path}, query={query}, ip={ip}"
    )
    print(f"[MediaMTX Auth] Full request: {request}")

    # Android 앱의 RTMP publish는 항상 허용
    if action == "publish" and protocol == "rtmp":
        print(f"[MediaMTX Auth] ✅ Allowing RTMP publish")
        return {"status": "ok"}

    # WebRTC publish (Teacher Screen Share) - WHIP
    if action == "publish" and protocol == "webrtc":
        # query에서 jwt 파라미터 추출
        token = None
        if "jwt=" in query:
            # 첫 번째 jwt= 값만 추출 (중복 방지)
            token = query.split("jwt=")[1].split("&")[0]
            print(f"[MediaMTX Auth] Extracted JWT token for publish: {token[:50]}...")

        if not token:
            print(f"[MediaMTX Auth] ❌ WebRTC publish denied - no token")
            raise HTTPException(status_code=401, detail="Token required")

        # 토큰 검증
        payload = verify_token(token)
        if not payload:
            print(f"[MediaMTX Auth] ❌ WebRTC publish denied - invalid token")
            raise HTTPException(status_code=401, detail="Invalid or expired token")

        # Teacher 권한 확인
        if payload.get("user_type") != "teacher":
            print(f"[MediaMTX Auth] ❌ WebRTC publish denied - not a teacher")
            raise HTTPException(status_code=403, detail="Only teachers can publish")

        print(
            f"[MediaMTX Auth] ✅ Allowing WebRTC publish for teacher {payload.get('user_id')}"
        )
        return {"status": "ok"}

    # Main 모드: 내부 프록시 스크립트의 RTMP read 허용 (localhost에서만)
    if action == "read" and protocol == "rtmp":
        ip = request.get("ip", "")
        if ip in ["127.0.0.1", "::1", "localhost"]:
            print(f"[MediaMTX Auth] ✅ Allowing internal RTMP read from {ip}")
            return {"status": "ok"}
        else:
            print(f"[MediaMTX Auth] ❌ RTMP read denied - not from localhost (ip={ip})")
            raise HTTPException(status_code=403, detail="RTMP read not allowed")

    # Main 모드: 내부 FFmpeg의 RTSP read 허용 (모든 localhost 연결)
    # FFmpeg 프록시는 항상 localhost에서만 실행되므로 RTSP read는 모두 허용
    if action == "read" and protocol == "rtsp":
        print(f"[MediaMTX Auth] ✅ Allowing internal RTSP read (FFmpeg proxy)")
        return {"status": "ok"}

    # WebRTC read는 JWT 토큰 필요
    if action == "read" and protocol == "webrtc":
        # query에서 jwt 파라미터 추출
        token = None
        if "jwt=" in query:
            # 첫 번째 jwt= 값만 추출 (중복 방지)
            token = query.split("jwt=")[1].split("&")[0]
            print(f"[MediaMTX Auth] Extracted JWT token: {token[:50]}...")

        if not token:
            print(f"[MediaMTX Auth] ❌ WebRTC read denied - no token")
            raise HTTPException(status_code=401, detail="Token required")

        # 토큰 검증
        payload = verify_token(token)
        if not payload:
            print(f"[MediaMTX Auth] ❌ WebRTC read denied - invalid token")
            raise HTTPException(status_code=401, detail="Invalid or expired token")

        # path 검증
        if payload.get("path") != path:
            print(
                f"[MediaMTX Auth] ❌ WebRTC read denied - path mismatch (expected: {payload.get('path')}, got: {path})"
            )
            raise HTTPException(status_code=403, detail="Path mismatch")

        print(f"[MediaMTX Auth] ✅ Allowing WebRTC read for {payload.get('user_id')}")
        return {"status": "ok"}

    # 그 외는 거부
    print(f"[MediaMTX Auth] ❌ Denied - action={action}, protocol={protocol}")
    raise HTTPException(status_code=403, detail="Access denied")
