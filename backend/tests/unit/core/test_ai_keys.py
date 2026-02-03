import os

import pytest


@pytest.fixture()
def fernet_key(monkeypatch):
    from cryptography.fernet import Fernet

    key = Fernet.generate_key().decode("utf-8")
    monkeypatch.setenv("AI_KEY_ENCRYPTION_KEY", key)
    return key


def test_encrypt_decrypt_roundtrip(fernet_key):
    from core.ai_keys import decrypt_api_key, encrypt_api_key

    plaintext = "test-gemini-key-123"
    token = encrypt_api_key(plaintext)
    assert token != plaintext

    restored = decrypt_api_key(token)
    assert restored == plaintext


def test_missing_master_key_raises(monkeypatch):
    monkeypatch.delenv("AI_KEY_ENCRYPTION_KEY", raising=False)

    from core.ai_keys import encrypt_api_key

    with pytest.raises(RuntimeError):
        encrypt_api_key("x")
