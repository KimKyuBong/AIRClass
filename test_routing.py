"""
스트리밍 라우팅 테스트 - Main 노드 제외 검증
"""

import sys

sys.path.insert(0, "/Users/hwansi/Project/AirClass/backend")

from core.cluster import ClusterManager, NodeInfo
from datetime import datetime


def test_main_node_excluded_from_routing():
    """Main 노드가 스트리밍 라우팅에서 제외되는지 테스트"""

    # ClusterManager 생성
    manager = ClusterManager()

    # Main 노드 등록
    main_node = NodeInfo(
        node_id="main",
        node_name="Main Node",
        host="localhost",
        port=8000,
        rtmp_port=1935,
        webrtc_port=8889,
        max_connections=0,  # Main은 무제한
        current_connections=0,
        cpu_usage=0.0,
        memory_usage=0.0,
        status="healthy",
        last_heartbeat=datetime.now(),
    )
    manager.register_node(main_node)
    manager.main_node_id = "main"

    # Sub 노드 2개 등록
    sub1 = NodeInfo(
        node_id="sub-1",
        node_name="Sub Node 1",
        host="localhost",
        port=8001,
        rtmp_port=1936,
        webrtc_port=8890,
        max_connections=150,
        current_connections=0,
        cpu_usage=0.0,
        memory_usage=0.0,
        status="healthy",
        last_heartbeat=datetime.now(),
    )
    manager.register_node(sub1)

    sub2 = NodeInfo(
        node_id="sub-2",
        node_name="Sub Node 2",
        host="localhost",
        port=8002,
        rtmp_port=1937,
        webrtc_port=8891,
        max_connections=150,
        current_connections=0,
        cpu_usage=0.0,
        memory_usage=0.0,
        status="healthy",
        last_heartbeat=datetime.now(),
    )
    manager.register_node(sub2)

    print("=" * 60)
    print("🧪 Main 노드 제외 라우팅 테스트")
    print("=" * 60)

    # 30개 스트림 라우팅 테스트
    routing_results = {}
    for i in range(30):
        stream_id = f"stream-{i:03d}"
        node = manager.get_node_for_stream(stream_id)

        if node:
            routing_results[node.node_id] = routing_results.get(node.node_id, 0) + 1

            # Main 노드로 라우팅되면 실패
            if node.node_id == "main":
                print(f"❌ FAIL: Stream {stream_id} routed to Main node!")
                return False
        else:
            print(f"❌ FAIL: No node selected for {stream_id}")
            return False

    print(f"\n✅ 라우팅 분산 결과:")
    for node_id, count in routing_results.items():
        percentage = (count / 30) * 100
        print(f"   {node_id}: {count}개 ({percentage:.1f}%)")

    # Main 노드가 라우팅 결과에 없어야 함
    if "main" in routing_results:
        print(f"\n❌ FAIL: Main node received {routing_results['main']} streams!")
        return False

    print(f"\n✅ PASS: Main 노드로 라우팅 안 됨")

    # 클러스터 통계 확인
    stats = manager.get_cluster_stats()
    print(f"\n📊 클러스터 통계 (Main 제외):")
    print(f"   전체 노드: {stats['total_nodes']}개")
    print(f"   정상 노드: {stats['healthy_nodes']}개")
    print(f"   전체 용량: {stats['total_capacity']}명")

    # Main 노드가 통계에서 제외되었는지 확인
    if stats["total_nodes"] != 2:
        print(f"\n❌ FAIL: Expected 2 nodes (Sub only), got {stats['total_nodes']}")
        return False

    if stats["total_capacity"] != 300:
        print(
            f"\n❌ FAIL: Expected 300 capacity (Sub only), got {stats['total_capacity']}"
        )
        return False

    print(f"\n✅ PASS: 클러스터 통계에서 Main 제외됨")

    # Sticky Session 테스트
    print(f"\n🔄 Sticky Session 테스트...")
    for i in range(30):
        stream_id = f"stream-{i:03d}"
        node1 = manager.get_node_for_stream(stream_id)
        node2 = manager.get_node_for_stream(stream_id)

        if node1.node_id != node2.node_id:
            print(f"❌ FAIL: Sticky session broken for {stream_id}")
            return False

    print(f"✅ PASS: 모든 스트림이 동일한 노드로 일관성 있게 라우팅됨")

    print("\n" + "=" * 60)
    print("🎉 모든 테스트 통과!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = test_main_node_excluded_from_routing()
    sys.exit(0 if success else 1)
