#!/usr/bin/env python3
"""
AIRClass Database Performance Benchmark
Phase 3-4: DB 쿼리 최적화 성능 측정
"""

import asyncio
import time
import random
from datetime import datetime, timedelta
from typing import Dict, List

from core.database import DatabaseManager, get_database_manager
from schemas import (
    Session,
    ChatMessage,
    StudentEngagement,
    QuizResponse,
    ScreenshotAnalysis,
)


class DatabaseBenchmark:
    def __init__(self):
        self.db: DatabaseManager = None
        self.test_session_id = "perf-test-001"
        self.benchmarks: Dict[str, float] = {}

    async def setup(self):
        """테스트 환경 준비"""
        print("=" * 70)
        print("🔧 Setting up test environment...")
        print("=" * 70)

        self.db = get_database_manager()
        if not self.db or not self.db.db:
            print("❌ Database not initialized")
            return False

        # 기존 테스트 데이터 삭제
        await self.cleanup()

        # 테스트 데이터 생성
        await self.create_test_data()

        print("✅ Setup complete\n")
        return True

    async def cleanup(self):
        """테스트 데이터 정리"""
        await self.db.db.chat_analytics.delete_many(
            {"session_id": self.test_session_id}
        )
        await self.db.db.student_engagement.delete_many(
            {"session_id": self.test_session_id}
        )
        await self.db.db.quiz_responses.delete_many(
            {"session_id": self.test_session_id}
        )
        await self.db.db.screenshot_analysis.delete_many(
            {"session_id": self.test_session_id}
        )

    async def create_test_data(self):
        """테스트 데이터 생성"""
        num_students = 100
        num_messages = 1000
        num_quizzes = 10

        print(f"  📝 Creating test data:")
        print(f"     - Students: {num_students}")
        print(f"     - Chat messages: {num_messages}")
        print(f"     - Quizzes: {num_quizzes}")

        # 1. 학생 참여도 데이터
        engagement_data = []
        for i in range(num_students):
            engagement = StudentEngagement(
                session_id=self.test_session_id,
                student_id=f"student-{i:03d}",
                attention_score=random.uniform(60, 100),
                participation_score=random.uniform(50, 100),
                quiz_accuracy=random.uniform(40, 100),
                overall_score=random.uniform(50, 100),
                engagement_level="high" if random.random() > 0.5 else "medium",
                activity_history=[],
                updated_at=datetime.utcnow(),
            )
            engagement_data.append(engagement.model_dump())

        await self.db.db.student_engagement.insert_many(engagement_data)

        # 2. 채팅 메시지 데이터
        chat_data = []
        base_time = datetime.utcnow() - timedelta(hours=2)
        for i in range(num_messages):
            student_id = f"student-{random.randint(0, num_students - 1):03d}"
            message = ChatMessage(
                message_id=f"msg-{i:04d}",
                session_id=self.test_session_id,
                student_id=student_id,
                user_type="student",
                content=f"Test message {i}",
                message_time=base_time + timedelta(seconds=i * 2),
                sentiment=random.choice(["positive", "neutral", "negative"]),
                sentiment_score=random.uniform(0, 1),
                intent=random.choice(["question", "answer", "comment", "confusion"]),
                intent_confidence=random.uniform(0.5, 1.0),
                keywords=[],
                learning_indicator=None,
                topic_relevance=random.uniform(0, 1),
                response_required=random.random() > 0.8,
                quality_score=random.uniform(0, 1),
            )
            chat_data.append(message.model_dump())

        await self.db.db.chat_analytics.insert_many(chat_data)

        # 3. 퀴즈 응답 데이터
        quiz_data = []
        for quiz_idx in range(num_quizzes):
            quiz_id = f"quiz-{quiz_idx:02d}"
            for student_idx in range(num_students):
                student_id = f"student-{student_idx:03d}"
                response = QuizResponse(
                    response_id=f"resp-{quiz_idx}-{student_idx}",
                    quiz_id=quiz_id,
                    session_id=self.test_session_id,
                    student_id=student_id,
                    answer="A",
                    is_correct=random.random() > 0.3,
                    response_time=random.uniform(5, 60),
                    responded_at=datetime.utcnow(),
                )
                quiz_data.append(response.model_dump())

        await self.db.db.quiz_responses.insert_many(quiz_data)

        print("  ✅ Test data created\n")

    async def benchmark_query(self, name: str, func, *args, **kwargs) -> float:
        """단일 쿼리 벤치마크"""
        start = time.time()
        result = await func(*args, **kwargs)
        duration = time.time() - start
        self.benchmarks[name] = duration
        return duration

    async def run_benchmarks(self):
        """모든 벤치마크 실행"""
        print("=" * 70)
        print("⏱️  Running Performance Benchmarks...")
        print("=" * 70)
        print()

        # 1. 채팅 메시지 조회
        duration = await self.benchmark_query(
            "Chat messages (all)", self.db.get_chat_messages, self.test_session_id
        )
        print(
            f"  1️⃣  Chat messages (1000 rows)".ljust(45) + f"{duration * 1000:7.2f} ms"
        )

        # 2. 채팅 메시지 조회 (최근 100개만)
        duration = await self.benchmark_query(
            "Chat messages (limit 100)",
            self.db.get_chat_messages,
            self.test_session_id,
            limit=100,
        )
        print(
            f"  2️⃣  Chat messages (limit 100)".ljust(45) + f"{duration * 1000:7.2f} ms"
        )

        # 3. 학생 참여도 조회 (전체)
        duration = await self.benchmark_query(
            "Engagement (full)",
            self.db.get_session_engagement,
            self.test_session_id,
            summary_only=False,
        )
        print(
            f"  3️⃣  Student engagement (100 students, full)".ljust(45)
            + f"{duration * 1000:7.2f} ms"
        )

        # 4. 학생 참여도 조회 (요약)
        duration = await self.benchmark_query(
            "Engagement (summary)",
            self.db.get_session_engagement,
            self.test_session_id,
            summary_only=True,
        )
        print(
            f"  4️⃣  Student engagement (100 students, summary)".ljust(45)
            + f"{duration * 1000:7.2f} ms"
        )

        # 5. 퀴즈 응답 조회
        duration = await self.benchmark_query(
            "Quiz responses", self.db.get_quiz_responses, "quiz-01"
        )
        print(
            f"  5️⃣  Quiz responses (100 responses)".ljust(45)
            + f"{duration * 1000:7.2f} ms"
        )

        # 6. 복합 쿼리 (대시보드 시뮬레이션)
        start = time.time()
        await asyncio.gather(
            self.db.get_chat_messages(self.test_session_id, limit=50),
            self.db.get_session_engagement(self.test_session_id, summary_only=True),
            self.db.get_quiz_responses("quiz-01"),
        )
        duration = time.time() - start
        self.benchmarks["Dashboard (parallel)"] = duration
        print(
            f"  6️⃣  Dashboard queries (parallel)".ljust(45)
            + f"{duration * 1000:7.2f} ms"
        )

        print()

    def print_results(self):
        """결과 요약"""
        print("=" * 70)
        print("📊 Benchmark Results Summary")
        print("=" * 70)
        print()

        # 목표 기준
        targets = {
            "Chat messages (all)": 100,  # 100ms
            "Chat messages (limit 100)": 50,  # 50ms
            "Engagement (full)": 100,  # 100ms
            "Engagement (summary)": 50,  # 50ms
            "Quiz responses": 80,  # 80ms
            "Dashboard (parallel)": 200,  # 200ms
        }

        passed = 0
        failed = 0

        for name, duration in self.benchmarks.items():
            duration_ms = duration * 1000
            target = targets.get(name, 100)

            if duration_ms < target:
                status = "✅ PASS"
                passed += 1
            elif duration_ms < target * 1.5:
                status = "⚠️  WARN"
            else:
                status = "❌ FAIL"
                failed += 1

            print(
                f"  {status}  {name.ljust(35)} {duration_ms:7.2f} ms (target: {target} ms)"
            )

        print()
        print("=" * 70)
        print(f"  Total: {len(self.benchmarks)} tests")
        print(f"  Passed: {passed}")
        print(f"  Failed: {failed}")
        print("=" * 70)

        if failed > 0:
            print()
            print("❌ Performance targets not met. Consider:")
            print("   - Add more indexes")
            print("   - Use projections to limit fields")
            print("   - Add query limits")
            print("   - Use aggregation pipelines")
        else:
            print()
            print("✅ All performance targets met! Database is well optimized.")

        return failed == 0

    async def run(self):
        """전체 벤치마크 실행"""
        if not await self.setup():
            return False

        await self.run_benchmarks()
        success = self.print_results()

        await self.cleanup()

        return success


async def main():
    """메인 함수"""
    benchmark = DatabaseBenchmark()
    success = await benchmark.run()

    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
