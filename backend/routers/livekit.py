"""
LiveKit Token API & Room Management
LiveKit JWT 토큰 발급 및 Room 관리
"""

from fastapi import APIRouter, HTTPException, Query
from livekit.api import AccessToken, VideoGrants
from livekit import api
import os

router = APIRouter(prefix="/api/livekit", tags=["livekit"])

# LiveKit 설정
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "AIRClass2025DevKey123456789ABC")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "AIRClass2025DevSecret123456789ABC")

# LiveKit 서버 URL
# - API 호출용: 컨테이너 내부 localhost 사용 (FastAPI → LiveKit 서버)
# - 클라이언트용: 외부 접속 가능한 SERVER_IP 사용 (브라우저 → LiveKit 서버)
LIVEKIT_API_URL = os.getenv("LIVEKIT_URL", "ws://localhost:7880")  # API 내부 호출
SERVER_IP = os.getenv("SERVER_IP", "localhost")
LIVEKIT_CLIENT_URL = f"ws://{SERVER_IP}:7880"  # 클라이언트 WebSocket URL

# LiveKit API 클라이언트 초기화 (HTTP URL로 변환)
LIVEKIT_HTTP_URL = LIVEKIT_API_URL.replace("ws://", "http://").replace("wss://", "https://")
lkapi = api.LiveKitAPI(url=LIVEKIT_HTTP_URL, api_key=LIVEKIT_API_KEY, api_secret=LIVEKIT_API_SECRET)
# 외부 접속을 위해 SERVER_IP 사용 (localhost는 외부에서 접근 불가)
SERVER_IP = os.getenv("SERVER_IP", "localhost")
LIVEKIT_URL = f"ws://{SERVER_IP}:7880"
LIVEKIT_HTTP_URL = f"http://{SERVER_IP}:7880"  # API 호출용 HTTP URL

# LiveKit API 클라이언트 초기화
lkapi = api.LiveKitAPI(url=LIVEKIT_HTTP_URL, api_key=LIVEKIT_API_KEY, api_secret=LIVEKIT_API_SECRET)


@router.post("/token")
async def create_livekit_token(
    user_id: str = Query(..., description="사용자 ID (고유)"),
    room_name: str = Query(..., description="방 이름 (예: math_class_101)"),
    user_type: str = Query(..., description="사용자 타입: teacher 또는 student"),
):
    """
    LiveKit JWT 토큰 발급

    LiveKit은 Redis를 통해 자동으로 클러스터링됩니다.
    모든 노드가 같은 Redis를 공유하므로, 어느 노드로든 접속 가능하며
    LiveKit이 자동으로 부하 분산을 처리합니다.

    - **user_id**: 고유 사용자 ID (예: "teacher_kim", "student_123")
    - **room_name**: 방 이름 (예: "math_class_101")
    - **user_type**: "teacher" (송출) 또는 "student" (수신)

    Returns:
        {
            "token": "eyJhbGc...",
            "url": "ws://10.100.0.146:7880",  # Main 노드 URL (LiveKit이 내부적으로 라우팅)
            "room_name": "math_class_101",
            "identity": "teacher_kim"
        }
    """
    try:
        # AccessToken 생성 (builder pattern)
        token = AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
        token.with_identity(user_id)
        token.with_name(user_id)

        # 권한 설정
        if user_type == "teacher":
            # Teacher: 방 생성, 송출, 녹화 가능
            grants = VideoGrants(
                room_join=True,
                room=room_name,
                can_publish=True,
                can_subscribe=True,
                can_publish_data=True,
                room_create=True,
                room_record=True,
            )
            token.with_grants(grants)
        elif user_type == "student":
            # Student: 수신만 가능
            grants = VideoGrants(
                room_join=True,
                room=room_name,
                can_publish=False,
                can_subscribe=True,
                can_publish_data=True,  # 채팅 등은 가능
            )
            token.with_grants(grants)
        else:
            raise HTTPException(status_code=400, detail="user_type must be 'teacher' or 'student'")

        # JWT 생성
        jwt_token = token.to_jwt()

        return {
            "token": jwt_token,
            "url": LIVEKIT_CLIENT_URL,  # Main 노드 URL (LiveKit이 자동 라우팅)
            "room_name": room_name,
            "identity": user_id,
            "user_type": user_type,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Token creation failed: {str(e)}")


@router.get("/rooms")
async def list_rooms():
    """
    활성 Room 목록 조회

    Returns:
        {
            "rooms": [
                {
                    "name": "class",
                    "num_participants": 2,
                    "creation_time": 1234567890,
                    "max_participants": 200
                }
            ]
        }
    """
    try:
        response = await lkapi.room.list_rooms(api.ListRoomsRequest())
        rooms = [
            {
                "name": room.name,
                "num_participants": room.num_participants,
                "creation_time": room.creation_time,
                "max_participants": room.max_participants,
                "empty_timeout": room.empty_timeout,
            }
            for room in response.rooms
        ]
        return {"rooms": rooms, "count": len(rooms)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list rooms: {str(e)}")


@router.get("/rooms/{room_name}/participants")
async def list_participants(room_name: str):
    """
    특정 Room의 참가자 목록 조회

    Args:
        room_name: 방 이름 (예: "class")

    Returns:
        {
            "room_name": "class",
            "participants": [
                {
                    "identity": "Teacher",
                    "name": "Teacher",
                    "state": "ACTIVE",
                    "is_publisher": true,
                    "joined_at": 1234567890
                }
            ]
        }
    """
    try:
        response = await lkapi.room.list_participants(api.ListParticipantsRequest(room=room_name))
        participants = [
            {
                "identity": p.identity,
                "name": p.name,
                "state": api.ParticipantInfo.State.Name(p.state),
                "is_publisher": p.is_publisher,
                "joined_at": p.joined_at,
                "num_tracks": len(p.tracks),
            }
            for p in response.participants
        ]
        return {
            "room_name": room_name,
            "participants": participants,
            "count": len(participants),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list participants: {str(e)}")


@router.delete("/rooms/{room_name}")
async def delete_room(room_name: str):
    """
    Room 삭제 (모든 참가자 강제 퇴장)

    Args:
        room_name: 삭제할 방 이름

    Returns:
        {"message": "Room deleted successfully"}
    """
    try:
        await lkapi.room.delete_room(api.DeleteRoomRequest(room=room_name))
        return {"message": f"Room '{room_name}' deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete room: {str(e)}")


@router.delete("/rooms/{room_name}/participants/{identity}")
async def remove_participant(room_name: str, identity: str):
    """
    특정 참가자 강제 퇴장

    Args:
        room_name: 방 이름
        identity: 퇴장시킬 참가자 ID

    Returns:
        {"message": "Participant removed successfully"}
    """
    try:
        await lkapi.room.remove_participant(
            api.RoomParticipantIdentity(room=room_name, identity=identity)
        )
        return {"message": f"Participant '{identity}' removed from room '{room_name}'"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove participant: {str(e)}")
