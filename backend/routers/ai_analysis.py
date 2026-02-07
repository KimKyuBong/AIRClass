"""
AIRClass AI Analysis API
AI 기반 분석 및 피드백 API 엔드포인트
"""

import hashlib
import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends, Query, File, UploadFile
from fastapi.responses import JSONResponse
from typing import Optional, List, Dict
from datetime import datetime

from services.ai.vision import get_vision_analyzer
from services.ai.nlp import get_nlp_analyzer
from services.ai.feedback import get_feedback_generator
from core.cache import get_cache
from core.database import get_database_manager
from services.ai.gemini import GeminiService
from core.ai_keys import (
    delete_teacher_gemini_key,
    get_env_gemini_key,
    get_teacher_gemini_key,
    has_teacher_gemini_key,
    upsert_teacher_gemini_key,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai", tags=["ai_analysis"])


# ============================================
# Dependencies
# ============================================


def get_vision():
    """VisionAnalyzer 의존성"""
    analyzer = get_vision_analyzer()
    if not analyzer:
        raise HTTPException(status_code=503, detail="Vision analyzer not initialized")
    return analyzer


def get_nlp():
    """NLPAnalyzer 의존성"""
    analyzer = get_nlp_analyzer()
    if not analyzer:
        raise HTTPException(status_code=503, detail="NLP analyzer not initialized")
    return analyzer


def get_feedback():
    """FeedbackGenerator 의존성"""
    generator = get_feedback_generator()
    if not generator:
        raise HTTPException(
            status_code=503, detail="Feedback generator not initialized"
        )
    return generator


def get_db():
    dbm = get_database_manager()
    if not dbm or not dbm.db:
        raise HTTPException(status_code=503, detail="Database not initialized")
    return dbm.db


# ============================================
# Vision Analysis Endpoints
# ============================================


@router.post("/vision/analyze-screenshot")
async def analyze_screenshot(
    session_id: str, screenshot_path: str, vision=Depends(get_vision)
):
    """
    스크린샷 분석

    Args:
        session_id: 세션 ID
        screenshot_path: 스크린샷 파일 경로

    Returns:
        ContentAnalysis: 분석 결과
    """
    try:
        cache = get_cache()
        cache_key = None
        if cache:
            try:
                p = Path(screenshot_path)
                st = p.stat()
                cache_key = (
                    f"airclass:cache:vision:{session_id}:"
                    f"{p.resolve().as_posix()}:{st.st_mtime_ns}:{st.st_size}"
                )
                cached = await cache.get_json(cache_key)
                if isinstance(cached, dict):
                    return JSONResponse(cached)
            except Exception:
                cache_key = None

        analysis = vision.analyze_screenshot(session_id, screenshot_path)
        payload = {
            "analysis_id": analysis.analysis_id,
            "session_id": analysis.session_id,
            "content_type": analysis.content_type,
            "topic": analysis.content_topic,
            "complexity_score": analysis.complexity_score,
            "engagement_potential": analysis.engagement_potential,
            "scene_description": analysis.scene_description,
            "recommendations": analysis.recommendations,
            "timestamp": analysis.timestamp,
        }

        if cache and cache_key:
            try:
                await cache.set_json(cache_key, payload, ttl_seconds=86400)
            except Exception:
                pass

        return JSONResponse(payload)
    except Exception as e:
        logger.error(f"❌ Failed to analyze screenshot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vision/{analysis_id}")
async def get_vision_analysis(analysis_id: str, vision=Depends(get_vision)):
    """비전 분석 결과 조회"""
    try:
        analysis = vision.get_analysis(analysis_id)
        if not analysis:
            raise HTTPException(status_code=404, detail="Analysis not found")

        return JSONResponse(
            {
                "analysis_id": analysis.analysis_id,
                "session_id": analysis.session_id,
                "content_type": analysis.content_type,
                "complexity_score": analysis.complexity_score,
                "engagement_potential": analysis.engagement_potential,
                "extracted_text": analysis.extracted_text[:200] + "..."
                if len(analysis.extracted_text) > 200
                else analysis.extracted_text,
                "recommendations": analysis.recommendations,
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to retrieve analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vision/session/{session_id}/analyses")
async def list_vision_analyses(session_id: str, vision=Depends(get_vision)):
    """세션별 비전 분석 목록"""
    try:
        analyses = vision.list_analyses(session_id)
        return JSONResponse(
            {
                "session_id": session_id,
                "count": len(analyses),
                "analyses": [
                    {
                        "analysis_id": a.analysis_id,
                        "content_type": a.content_type,
                        "complexity_score": a.complexity_score,
                        "timestamp": a.timestamp,
                    }
                    for a in analyses
                ],
            }
        )
    except Exception as e:
        logger.error(f"❌ Failed to list analyses: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# NLP Analysis Endpoints
# ============================================


@router.post("/nlp/analyze-message")
async def analyze_message(
    session_id: str,
    message_id: str,
    user_id: str,
    user_type: str,  # "teacher" or "student"
    content: str,
    nlp=Depends(get_nlp),
):
    """
    메시지 분석

    Args:
        session_id: 세션 ID
        message_id: 메시지 ID
        user_id: 사용자 ID
        user_type: 사용자 타입
        content: 메시지 내용

    Returns:
        ChatMessage: 분석된 메시지
    """
    try:
        cache = get_cache()
        cache_key = None
        if cache:
            try:
                content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
                cache_key = (
                    f"airclass:cache:nlp:{session_id}:{message_id}:{content_hash}"
                )
                cached = await cache.get_json(cache_key)
                if isinstance(cached, dict):
                    return JSONResponse(cached)
            except Exception:
                cache_key = None

        message = nlp.analyze_message(
            session_id=session_id,
            message_id=message_id,
            user_id=user_id,
            user_type=user_type,
            content=content,
        )

        payload = {
            "message_id": message.message_id,
            "sentiment": message.sentiment,
            "sentiment_score": message.sentiment_score,
            "intent": message.intent,
            "intent_confidence": message.intent_confidence,
            "keywords": message.keywords,
            "learning_indicator": message.learning_indicator,
            "topic_relevance": message.topic_relevance,
            "response_required": message.response_required,
            "quality_score": message.quality_score,
        }

        if cache and cache_key:
            try:
                await cache.set_json(cache_key, payload, ttl_seconds=3600)
            except Exception:
                pass

        return JSONResponse(payload)
    except Exception as e:
        logger.error(f"❌ Failed to analyze message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/nlp/{message_id}")
async def get_message_analysis(message_id: str, nlp=Depends(get_nlp)):
    """메시지 분석 결과 조회"""
    try:
        message = nlp.get_message(message_id)
        if not message:
            raise HTTPException(status_code=404, detail="Message not found")

        return JSONResponse(
            {
                "message_id": message.message_id,
                "content": message.content,
                "sentiment": message.sentiment,
                "intent": message.intent,
                "keywords": message.keywords,
                "timestamp": message.timestamp,
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to retrieve message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/nlp/session/{session_id}/messages")
async def list_session_messages(session_id: str, nlp=Depends(get_nlp)):
    """세션별 메시지 분석 목록"""
    try:
        messages = nlp.list_messages_by_session(session_id)
        return JSONResponse(
            {
                "session_id": session_id,
                "count": len(messages),
                "messages": [
                    {
                        "message_id": m.message_id,
                        "user_id": m.user_id,
                        "sentiment": m.sentiment,
                        "intent": m.intent,
                        "content": m.content[:100] + "..."
                        if len(m.content) > 100
                        else m.content,
                    }
                    for m in messages
                ],
            }
        )
    except Exception as e:
        logger.error(f"❌ Failed to list messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/nlp/summarize-conversation")
async def summarize_conversation(session_id: str, nlp=Depends(get_nlp)):
    """대화 요약"""
    try:
        summary = nlp.summarize_conversation(session_id)
        return JSONResponse(
            {
                "session_id": summary.session_id,
                "summary": summary.summary,
                "main_topics": summary.main_topics,
                "key_questions": summary.key_questions,
                "understanding_level": summary.student_understanding_level,
                "engagement_level": summary.engagement_level,
                "areas_for_review": summary.areas_needing_review,
            }
        )
    except Exception as e:
        logger.error(f"❌ Failed to summarize conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Feedback Generation Endpoints
# ============================================


@router.post("/feedback/generate-student")
async def generate_student_feedback(
    session_id: str,
    student_id: str,
    topic: str,
    is_correct: bool = False,
    response_time: float = 0,
    attempt_count: int = 1,
    feedback=Depends(get_feedback),
):
    """
    학생 피드백 생성

    Args:
        session_id: 세션 ID
        student_id: 학생 ID
        topic: 주제
        is_correct: 정답 여부
        response_time: 응답 시간
        attempt_count: 시도 횟수

    Returns:
        StudentFeedback: 생성된 피드백
    """
    try:
        cache = get_cache()
        cache_key = None
        if cache:
            try:
                cache_key = (
                    f"airclass:cache:feedback_student:{session_id}:"
                    f"{student_id}:{topic}:{int(is_correct)}:{attempt_count}:{int(response_time)}"
                )
                cached = await cache.get_json(cache_key)
                if isinstance(cached, dict):
                    return JSONResponse(cached)
            except Exception:
                cache_key = None

        content_analysis = {"topic": topic}
        message_analysis = {"learning_indicator": None}
        performance_data = {
            "is_correct": is_correct,
            "response_time": response_time,
            "attempt_count": attempt_count,
        }

        student_feedback = feedback.generate_student_feedback(
            session_id=session_id,
            student_id=student_id,
            topic=topic,
            content_analysis=content_analysis,
            message_analysis=message_analysis,
            performance_data=performance_data,
        )

        payload = {
            "feedback_id": student_feedback.feedback_id,
            "type": student_feedback.feedback_type,
            "message": student_feedback.message,
            "explanation": student_feedback.explanation,
            "examples": student_feedback.examples,
            "resources": student_feedback.resources,
            "priority": student_feedback.priority,
        }

        if cache and cache_key:
            try:
                await cache.set_json(cache_key, payload, ttl_seconds=3600)
            except Exception:
                pass

        return JSONResponse(payload)
    except Exception as e:
        logger.error(f"❌ Failed to generate student feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/feedback/generate-teacher-insight")
async def generate_teacher_insight(
    session_id: str, message_count: int = 0, feedback=Depends(get_feedback)
):
    """
    교사 인사이트 생성

    Args:
        session_id: 세션 ID
        message_count: 메시지 수

    Returns:
        TeacherInsight: 교사 인사이트
    """
    try:
        class_data = {"student_count": 20}
        message_analytics = []  # 실제로는 메시지 분석 데이터
        performance_analytics = {}

        insight = feedback.generate_teacher_insight(
            session_id=session_id,
            class_data=class_data,
            message_analytics=message_analytics,
            performance_analytics=performance_analytics,
        )

        return JSONResponse(
            {
                "insight_id": insight.insight_id,
                "engagement_level": insight.class_engagement_level,
                "understanding_level": insight.average_understanding_level,
                "sentiment": insight.class_sentiment,
                "struggling_students": insight.struggling_students,
                "high_performers": insight.high_performers,
                "pacing": insight.pacing_assessment,
                "confusing_topics": insight.most_confusing_topics,
                "recommendations": insight.recommendations,
            }
        )
    except Exception as e:
        logger.error(f"❌ Failed to generate teacher insight: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/feedback/{feedback_id}")
async def get_feedback_data(feedback_id: str, feedback=Depends(get_feedback)):
    """피드백 데이터 조회"""
    try:
        fb = feedback.get_feedback(feedback_id)
        if not fb:
            raise HTTPException(status_code=404, detail="Feedback not found")

        return JSONResponse(
            {
                "feedback_id": fb.feedback_id,
                "student_id": fb.student_id,
                "type": fb.feedback_type,
                "message": fb.message,
                "priority": fb.priority,
                "timestamp": fb.timestamp,
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to retrieve feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Integrated Analysis Endpoints
# ============================================


@router.post("/analysis/comprehensive")
async def comprehensive_analysis(
    session_id: str,
    screenshot_path: Optional[str] = None,
    messages: Optional[List[Dict]] = None,
    vision=Depends(get_vision),
    nlp=Depends(get_nlp),
    feedback=Depends(get_feedback),
):
    """
    종합 분석
    비전, NLP, 피드백을 모두 포함한 종합 분석

    Args:
        session_id: 세션 ID
        screenshot_path: 스크린샷 경로 (선택)
        messages: 메시지 목록 (선택)

    Returns:
        dict: 종합 분석 결과
    """
    try:
        result = {
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "vision_analysis": None,
            "nlp_analysis": None,
            "feedback": None,
        }

        cache = get_cache()

        # 비전 분석
        if screenshot_path:
            try:
                cached_vision = None
                cache_key = None
                if cache:
                    try:
                        p = Path(screenshot_path)
                        st = p.stat()
                        cache_key = (
                            f"airclass:cache:vision:{session_id}:"
                            f"{p.resolve().as_posix()}:{st.st_mtime_ns}:{st.st_size}"
                        )
                        cached_vision = await cache.get_json(cache_key)
                    except Exception:
                        cache_key = None

                if isinstance(cached_vision, dict):
                    result["vision_analysis"] = {
                        "analysis_id": cached_vision.get("analysis_id"),
                        "content_type": cached_vision.get("content_type"),
                        "complexity_score": cached_vision.get("complexity_score"),
                    }
                else:
                    vision_result = vision.analyze_screenshot(
                        session_id, screenshot_path
                    )
                    result["vision_analysis"] = {
                        "analysis_id": vision_result.analysis_id,
                        "content_type": vision_result.content_type,
                        "complexity_score": vision_result.complexity_score,
                    }

                    if cache and cache_key:
                        try:
                            await cache.set_json(
                                cache_key,
                                {
                                    "analysis_id": vision_result.analysis_id,
                                    "session_id": vision_result.session_id,
                                    "content_type": vision_result.content_type,
                                    "topic": vision_result.content_topic,
                                    "complexity_score": vision_result.complexity_score,
                                    "engagement_potential": vision_result.engagement_potential,
                                    "scene_description": vision_result.scene_description,
                                    "recommendations": vision_result.recommendations,
                                    "timestamp": vision_result.timestamp,
                                },
                                ttl_seconds=86400,
                            )
                        except Exception:
                            pass
            except Exception as e:
                logger.warning(f"⚠️ Vision analysis failed: {e}")

        # NLP 분석
        if messages:
            try:
                nlp_results = []
                for msg in messages[:5]:  # 최대 5개 메시지
                    msg_session_id = msg.get("session_id", session_id)
                    msg_message_id = msg.get("message_id", "unknown")
                    msg_user_id = msg.get("user_id", "unknown")
                    msg_user_type = msg.get("user_type", "student")
                    msg_content = msg.get("content", "")

                    cached_nlp = None
                    cache_key = None
                    if cache:
                        try:
                            content_hash = hashlib.sha256(
                                msg_content.encode("utf-8")
                            ).hexdigest()
                            cache_key = (
                                f"airclass:cache:nlp:{msg_session_id}:"
                                f"{msg_message_id}:{content_hash}"
                            )
                            cached_nlp = await cache.get_json(cache_key)
                        except Exception:
                            cache_key = None

                    if isinstance(cached_nlp, dict):
                        nlp_results.append(
                            {
                                "message_id": cached_nlp.get("message_id"),
                                "sentiment": cached_nlp.get("sentiment"),
                                "intent": cached_nlp.get("intent"),
                            }
                        )
                        continue

                    nlp_msg = nlp.analyze_message(
                        session_id=msg_session_id,
                        message_id=msg_message_id,
                        user_id=msg_user_id,
                        user_type=msg_user_type,
                        content=msg_content,
                    )
                    nlp_results.append(
                        {
                            "message_id": nlp_msg.message_id,
                            "sentiment": nlp_msg.sentiment,
                            "intent": nlp_msg.intent,
                        }
                    )

                    if cache and cache_key:
                        try:
                            await cache.set_json(
                                cache_key,
                                {
                                    "message_id": nlp_msg.message_id,
                                    "sentiment": nlp_msg.sentiment,
                                    "sentiment_score": nlp_msg.sentiment_score,
                                    "intent": nlp_msg.intent,
                                    "intent_confidence": nlp_msg.intent_confidence,
                                    "keywords": nlp_msg.keywords,
                                    "learning_indicator": nlp_msg.learning_indicator,
                                    "topic_relevance": nlp_msg.topic_relevance,
                                    "response_required": nlp_msg.response_required,
                                    "quality_score": nlp_msg.quality_score,
                                },
                                ttl_seconds=3600,
                            )
                        except Exception:
                            pass
                result["nlp_analysis"] = nlp_results
            except Exception as e:
                logger.warning(f"⚠️ NLP analysis failed: {e}")

        return JSONResponse(result)
    except Exception as e:
        logger.error(f"❌ Comprehensive analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Health Check
# ============================================


@router.get("/health")
async def health_check(
    vision=Depends(get_vision), nlp=Depends(get_nlp), feedback=Depends(get_feedback)
):
    """AI 분석 시스템 헬스 체크"""
    return JSONResponse(
        {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "services": {
                "vision": "ready" if vision else "unavailable",
                "nlp": "ready" if nlp else "unavailable",
                "feedback": "ready" if feedback else "unavailable",
            },
        }
    )


# ============================================
# Teacher Gemini Key Management
# ============================================


@router.post("/keys/gemini")
async def set_teacher_gemini_key(
    teacher_id: str,
    api_key: str,
    db=Depends(get_db),
):
    """교사 Gemini API Key 저장(암호화)"""
    try:
        await upsert_teacher_gemini_key(db, teacher_id=teacher_id, api_key=api_key)
        return JSONResponse(
            {"teacher_id": teacher_id, "provider": "gemini", "enabled": True}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/keys/gemini/status")
async def get_teacher_gemini_key_status(teacher_id: str):
    """교사 Gemini Key 활성화 여부(키 값은 반환하지 않음). DB/설정 오류 시에도 200으로 안전 응답."""
    try:
        dbm = get_database_manager()
        if dbm and dbm.db:
            enabled = await has_teacher_gemini_key(dbm.db, teacher_id=teacher_id)
        else:
            enabled = False
        env_enabled = bool(get_env_gemini_key())
        return JSONResponse(
            {
                "teacher_id": teacher_id,
                "provider": "gemini",
                "enabled": enabled,
                "env_fallback_available": env_enabled,
            }
        )
    except Exception as e:
        logger.warning("Gemini status check failed (returning safe defaults): %s", e)
        return JSONResponse(
            {
                "teacher_id": teacher_id,
                "provider": "gemini",
                "enabled": False,
                "env_fallback_available": bool(get_env_gemini_key()),
            }
        )


@router.delete("/keys/gemini")
async def delete_teacher_gemini_key_endpoint(
    teacher_id: str,
    db=Depends(get_db),
):
    """교사 Gemini API Key 삭제"""
    try:
        deleted = await delete_teacher_gemini_key(db, teacher_id=teacher_id)
        return JSONResponse(
            {"teacher_id": teacher_id, "provider": "gemini", "deleted": deleted}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Gemini (Test) Endpoint
# ============================================


@router.post("/gemini/generate")
async def gemini_generate(
    prompt: str,
    teacher_id: Optional[str] = None,
    model: str = "gemini-1.5-flash",
    db=Depends(get_db),
):
    """테스트용 Gemini 호출(교사 키 -> env fallback)."""
    api_key = None
    if teacher_id:
        api_key = await get_teacher_gemini_key(db, teacher_id=teacher_id)

    if not api_key:
        api_key = get_env_gemini_key()

    if not api_key:
        raise HTTPException(
            status_code=400,
            detail="Gemini API key not configured (teacher key or GEMINI_API_KEY)",
        )

    try:
        svc = GeminiService(api_key=api_key)
        text = await svc.generate(model=model, prompt=prompt)
        return JSONResponse({"model": model, "text": text})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
