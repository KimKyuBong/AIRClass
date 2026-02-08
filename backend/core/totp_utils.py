"""
TOTP(시간 기반 일회용 비밀번호) 유틸리티

.env의 TOTP_SECRET으로 6자리 코드 검증·프로비저닝 URI 생성.
QR 스캔 후 어떤 TOTP 호환 앱(Google Authenticator, Authy 등)이든 사용 가능.
"""

import os
import logging
from typing import Optional, Tuple

logger = logging.getLogger("uvicorn")

try:
    import pyotp
except ImportError:
    pyotp = None  # type: ignore


def get_totp_secret() -> Optional[str]:
    """환경변수 TOTP_SECRET 반환 (없으면 None)."""
    return os.getenv("TOTP_SECRET") or None


def generate_totp_secret() -> str:
    """새 TOTP 시크릿 생성 (base32). .env 최초 설정 시 사용."""
    if not pyotp:
        raise RuntimeError("pyotp not installed")
    return pyotp.random_base32()


def verify_totp_code(secret: str, code: str, valid_window: int = 1) -> bool:
    """
    TOTP 6자리 코드 검증.
    valid_window: 허용할 시간 창 (0=현재 30초만, 1=앞뒤 30초 포함).
    """
    if not pyotp or not secret or not code:
        return False
    code = code.strip().replace(" ", "")
    if len(code) != 6 or not code.isdigit():
        return False
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=valid_window)


def get_provisioning_uri(
    secret: str,
    issuer: str = "AIRClass",
    account_name: str = "cluster",
) -> str:
    """QR에 넣을 otpauth URI. 앱에서 이 URI로 등록하면 6자리 코드 생성."""
    if not pyotp:
        raise RuntimeError("pyotp not installed")
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=account_name, issuer_name=issuer)


def get_current_totp_code(secret: str) -> Optional[str]:
    """현재 시각 기준 6자리 코드 생성. Sub 노드·자동화에서 사용."""
    if not pyotp or not secret:
        return None
    return pyotp.TOTP(secret).now()
