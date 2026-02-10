"""
TOTP(시간 기반 일회용 비밀번호) 유틸리티

.env의 TOTP_SECRET으로 6자리 코드 검증·프로비저닝 URI 생성.
QR 스캔 후 어떤 TOTP 호환 앱(Google Authenticator, Authy 등)이든 사용 가능.
"""

import os
import logging
import time
from typing import Optional, Tuple, Dict

logger = logging.getLogger("uvicorn")

# 재생 공격 방지를 위한 사용된 코드 저장소 (메모리)
# {code: expiration_timestamp}
_used_codes: Dict[str, float] = {}

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
    재생 공격 방지 및 시간 동기화 검증 포함.
    valid_window: 허용할 시간 창 (0=현재 30초만, 1=앞뒤 30초 포함).
    """
    if not pyotp or not secret or not code:
        return False

    code = code.strip().replace(" ", "")
    if len(code) != 6 or not code.isdigit():
        return False

    # 1. 이미 사용된 코드인지 체크 (재생 공격 방지)
    current_time = time.time()
    if code in _used_codes:
        if _used_codes[code] > current_time:
            logger.warning(f"Replay attack detected for code: {code}")
            return False
        else:
            # 만료된 코드는 삭제
            del _used_codes[code]

    # 2. TOTP 검증
    totp = pyotp.TOTP(secret)
    is_valid = totp.verify(code, valid_window=valid_window)

    if is_valid:
        # 3. 사용된 코드로 마킹 (30초 * (valid_window * 2 + 1) 동안 유효)
        # 보통 30초 단위이므로, valid_window=1이면 앞뒤 30초 포함 총 90초 동안 유효할 수 있음
        expiry = current_time + (30 * (valid_window * 2 + 1))
        _used_codes[code] = expiry

        # 오래된 코드 정리 (가끔 수행)
        if len(_used_codes) > 100:
            expired = [c for c, t in _used_codes.items() if t < current_time]
            for c in expired:
                del _used_codes[c]

    return is_valid


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
