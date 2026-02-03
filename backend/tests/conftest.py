"""
Pytest configuration for AIRClass tests
테스트 시 필요한 설정 및 픽스처 정의
"""

import sys
import os
import pytest
import pytest_asyncio

# Backend 디렉토리를 Python 경로에 추가
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

# schemas 패키지를 models로 aliasing (backward compatibility)
import schemas

sys.modules["models"] = schemas

print(f"✅ Pytest configured: backend_dir={backend_dir}")


# pytest-asyncio 설정
pytest_plugins = ("pytest_asyncio",)


# ============================================
# Database Fixtures (동기 방식 - Motor 대신 pymongo 사용)
# ============================================


@pytest.fixture(scope="session")
def mongo_url():
    """MongoDB URL"""
    return os.getenv(
        "MONGO_URL",
        "mongodb://airclass:airclass2025@localhost:27017/airclass_test?authSource=admin",
    )


@pytest.fixture(scope="function")
def db(mongo_url):
    """동기 MongoDB 클라이언트 (테스트용)"""
    from pymongo import MongoClient
    from pymongo.database import Database

    client = MongoClient(mongo_url)
    db = client["airclass_test"]

    # 테스트 전 DB 초기화
    db.quizzes.delete_many({})
    db.quiz_responses.delete_many({})
    db.sessions.delete_many({})
    db.student_engagement.delete_many({})
    db.chat_analytics.delete_many({})
    db.screenshot_analysis.delete_many({})

    yield db

    # Cleanup
    client.close()


@pytest_asyncio.fixture(scope="function")
async def db_manager(mongo_url):
    """DatabaseManager fixture (비동기 테스트용)"""
    from core.database import DatabaseManager
    import core.database

    # DatabaseManager 인스턴스 생성
    manager = DatabaseManager(mongo_url)

    # 비동기 초기화
    initialized = await manager.init()

    if not initialized:
        raise RuntimeError("Failed to initialize DatabaseManager")

    # 테스트 전 DB 초기화
    await manager.db.quizzes.delete_many({})
    await manager.db.quiz_responses.delete_many({})
    await manager.db.sessions.delete_many({})
    await manager.db.student_engagement.delete_many({})
    await manager.db.chat_analytics.delete_many({})
    await manager.db.screenshot_analysis.delete_many({})

    # 전역 db_manager 교체
    original_manager = core.database.db_manager
    core.database.db_manager = manager

    yield manager

    # Cleanup
    if hasattr(manager, "client") and manager.client:
        manager.client.close()
    core.database.db_manager = original_manager


# ============================================
# FastAPI Application Fixtures
# ============================================


@pytest_asyncio.fixture
async def app(db_manager):
    """FastAPI 앱 (DB 연결 포함)"""
    from main import app

    # DB 의존성을 테스트용으로 교체
    from core.database import get_database_manager

    app.dependency_overrides[get_database_manager] = lambda: db_manager

    yield app

    # Cleanup
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def async_client(app):
    """비동기 HTTP 클라이언트 (실제 DB 사용)"""
    from httpx import ASGITransport, AsyncClient

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
