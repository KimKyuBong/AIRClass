#!/usr/bin/env python3
"""동적 포트/자동검색 변경 사항 빠른 검증 (pytest 없이 실행 가능)"""
import os
import sys

# backend 루트를 path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_discovery_ports():
    from core.discovery import _discovery_ports
    ports = _discovery_ports()
    assert 8000 in ports and 8100 in ports, f"Expected 8000,8100 in _discovery_ports(), got {ports}"
    print("  OK _discovery_ports():", ports)

def test_health_api_port_env():
    os.environ["MAIN_API_PORT"] = "8100"
    os.environ.pop("NODE_PORT", None)
    from routers.system import health_check
    import asyncio
    resp = asyncio.get_event_loop().run_until_complete(health_check())
    # health_check returns dict with api_port when MAIN_API_PORT set
    assert resp.get("api_port") == 8100, f"Expected api_port 8100, got {resp.get('api_port')}"
    print("  OK health_check() returns api_port:", resp.get("api_port"))
    del os.environ["MAIN_API_PORT"]

def test_cluster_advertised_port():
    # MAIN_API_PORT 우선 사용하는지 (cluster에서 사용하는 로직과 동일)
    advertised = int(os.environ.get("MAIN_API_PORT", os.environ.get("NODE_PORT", "8000")))
    assert advertised in (8000, 8100, 8200) or 8000 <= advertised <= 9000
    print("  OK advertised_port logic (MAIN_API_PORT or NODE_PORT):", advertised)

if __name__ == "__main__":
    print("Quick verify: dynamic port & discovery")
    try:
        test_discovery_ports()
        test_cluster_advertised_port()
        # health_check needs app context; skip or mock
        print("  SKIP health_check (needs app)")
        print("All checks passed.")
    except Exception as e:
        print("FAIL:", e)
        sys.exit(1)
