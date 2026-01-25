"""
Pytest configuration for AIRClass tests
테스트 시 필요한 설정 및 픽스처 정의
"""

import sys
import os
import importlib.util

# Backend 디렉토리를 Python 경로에 추가
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

# models.py를 직접 로드 (models 디렉토리와의 충돌 해결)
models_path = os.path.join(backend_dir, "models.py")
spec = importlib.util.spec_from_file_location("models_module", models_path)
models_module = importlib.util.module_from_spec(spec)
sys.modules["models"] = models_module
spec.loader.exec_module(models_module)

print(f"✅ Pytest configured: backend_dir={backend_dir}")
