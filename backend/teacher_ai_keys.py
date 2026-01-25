import base64
import logging
import os
from datetime import datetime
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)


def _get_fernet() -> Fernet:
    key = os.getenv("AI_KEY_ENCRYPTION_KEY")
    if not key:
        raise RuntimeError("AI_KEY_ENCRYPTION_KEY is not set")
    try:
        raw = key.encode("utf-8")
        # Accept either raw 32-byte base64 key or plain text that is base64-url-safe.
        return Fernet(raw)
    except Exception as e:
        raise RuntimeError("Invalid AI_KEY_ENCRYPTION_KEY (must be Fernet key)") from e


def encrypt_api_key(plaintext: str) -> str:
    f = _get_fernet()
    token = f.encrypt(plaintext.encode("utf-8"))
    return token.decode("utf-8")


def decrypt_api_key(token: str) -> str:
    f = _get_fernet()
    try:
        pt = f.decrypt(token.encode("utf-8"))
    except InvalidToken as e:
        raise RuntimeError("Invalid encrypted api key") from e
    return pt.decode("utf-8")


async def upsert_teacher_gemini_key(db, teacher_id: str, api_key: str) -> None:
    encrypted = encrypt_api_key(api_key)
    now = datetime.utcnow()
    await db.teacher_ai_keys.update_one(
        {"teacher_id": teacher_id, "provider": "gemini"},
        {
            "$set": {
                "encrypted_api_key": encrypted,
                "updated_at": now,
            },
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
    )


async def delete_teacher_gemini_key(db, teacher_id: str) -> bool:
    result = await db.teacher_ai_keys.delete_one(
        {"teacher_id": teacher_id, "provider": "gemini"}
    )
    return result.deleted_count > 0


async def has_teacher_gemini_key(db, teacher_id: str) -> bool:
    doc = await db.teacher_ai_keys.find_one(
        {"teacher_id": teacher_id, "provider": "gemini"},
        projection={"_id": 1},
    )
    return doc is not None


async def get_teacher_gemini_key(db, teacher_id: str) -> Optional[str]:
    doc = await db.teacher_ai_keys.find_one(
        {"teacher_id": teacher_id, "provider": "gemini"},
        projection={"encrypted_api_key": 1},
    )
    if not doc or "encrypted_api_key" not in doc:
        return None
    try:
        return decrypt_api_key(doc["encrypted_api_key"])
    except Exception as e:
        logger.error(
            f"❌ Failed to decrypt Gemini key for teacher_id={teacher_id}: {e}"
        )
        return None


def get_env_gemini_key() -> Optional[str]:
    return os.getenv("GEMINI_API_KEY")
