"""
JWT Token Authentication
스트림 접근을 위한 JWT 토큰 생성 및 검증
"""

import jwt
import secrets
import os
import logging
from datetime import datetime, timedelta, UTC
from typing import Optional, Set

logger = logging.getLogger(__name__)

# JWT 설정 (환경 변수에서 읽기, 없으면 생성)
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_MINUTES = 60  # 토큰 유효 시간 (export를 위해 모듈 레벨에 정의)

# Active tokens (간단한 토큰 관리)
_active_tokens: Set[str] = set()


def generate_stream_token(user_type: str, user_id: str, action: str = "read") -> str:
    """
    스트림 접근 토큰 생성

    Args:
        user_type: 'teacher', 'student', 'monitor'
        user_id: 사용자 ID (학생 이름 등)
        action: 'read' (default) or 'publish'

    Returns:
        JWT 토큰 문자열
    """
    expiration = datetime.now(UTC) + timedelta(minutes=JWT_EXPIRATION_MINUTES)
    payload = {
        "user_type": user_type,
        "user_id": user_id,
        "exp": expiration,
        "iat": datetime.now(UTC),
        "action": action,  # MediaMTX action
        "path": "live/stream",  # MediaMTX path
    }
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    _active_tokens.add(token)

    logger.debug(f"Generated token for {user_type}/{user_id} (action: {action})")
    return token


def generate_device_token(expires_minutes: int = 15) -> str:
    """
    TOTP 검증 후 발급하는 디바이스(Android 등) 연동용 단기 JWT.
    payload에 scope: "device" 포함.
    """
    expiration = datetime.now(UTC) + timedelta(minutes=expires_minutes)
    payload = {
        "scope": "device",
        "exp": expiration,
        "iat": datetime.now(UTC),
    }
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    _active_tokens.add(token)
    return token


def verify_token(token: str) -> Optional[dict]:
    """
    토큰 검증

    Args:
        token: JWT 토큰 문자열

    Returns:
        검증 성공 시 payload dict, 실패 시 None
    """
    try:
        # JWT 검증만 수행 (active_tokens는 Main에서만 관리하므로 Sub에서는 체크하지 않음)
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        logger.debug(f"✅ Token valid. Payload: {payload}")
        return payload
    except jwt.ExpiredSignatureError as e:
        logger.warning(f"❌ Token expired: {e}")
        # Main에서만 active_tokens 정리
        if token in _active_tokens:
            _active_tokens.discard(token)
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"❌ Invalid token: {e}")
        return None


def revoke_token(token: str) -> bool:
    """
    토큰 무효화

    Args:
        token: 무효화할 JWT 토큰

    Returns:
        무효화 성공 여부
    """
    if token in _active_tokens:
        _active_tokens.discard(token)
        logger.info(f"Token revoked: {token[:20]}...")
        return True
    return False


def get_active_token_count() -> int:
    """활성 토큰 개수 반환"""
    return len(_active_tokens)


def clear_expired_tokens() -> int:
    """
    만료된 토큰 정리

    Returns:
        정리된 토큰 개수
    """
    expired_tokens = []
    for token in _active_tokens:
        try:
            jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        except jwt.ExpiredSignatureError:
            expired_tokens.append(token)
        except jwt.InvalidTokenError:
            expired_tokens.append(token)

    for token in expired_tokens:
        _active_tokens.discard(token)

    if expired_tokens:
        logger.info(f"Cleared {len(expired_tokens)} expired tokens")

    return len(expired_tokens)


def is_token_active(token: str) -> bool:
    """토큰이 활성 상태인지 확인"""
    return token in _active_tokens
