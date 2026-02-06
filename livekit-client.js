// LiveKit Client JavaScript
// Separated from test_livekit.html for maintainability

let room = null;
let localVideoTrack = null;
let LivekitClient = null;
let elements = {};

function initElements() {
    elements = {
        nodeSelect: document.getElementById("nodeSelect"),
        userType: document.getElementById("userType"),
        userId: document.getElementById("userId"),
        roomName: document.getElementById("roomName"),
        connectBtn: document.getElementById("connectBtn"),
        disconnectBtn: document.getElementById("disconnectBtn"),
        shareBtn: document.getElementById("shareBtn"),
        status: document.getElementById("status"),
        videoGrid: document.getElementById("videoGrid"),
        localVideo: document.getElementById("localVideo"),
        participantsList: document.getElementById("participantsList"),
        participantCount: document.getElementById("participantCount"),
        videoCount: document.getElementById("videoCount"),
        audioCount: document.getElementById("audioCount"),
        logs: document.getElementById("logs"),
    };
}

function log(message, type = "info") {
    const time = new Date().toLocaleTimeString("ko-KR");
    const entry = document.createElement("div");
    entry.className = "log-entry";
    entry.innerHTML = `<span class="log-time">${time}</span><span>${message}</span>`;
    elements.logs.appendChild(entry);
    elements.logs.scrollTop = elements.logs.scrollHeight;
    console.log(`[${time}] ${message}`);
}

function updateStatus(status, message) {
    elements.status.className = `status status-${status}`;
    const emoji =
        status === "connected"
            ? "✅"
            : status === "connecting"
              ? "🔄"
              : "⭕";
    elements.status.textContent = `${emoji} ${message}`;
}

function updateStats() {
    if (!room || !room.participants) {
        elements.participantCount.textContent = "0";
        elements.videoCount.textContent = "0";
        elements.audioCount.textContent = "0";
        return;
    }

    const { Track } = LivekitClient;
    const participants = Array.from(room.participants.values());
    elements.participantCount.textContent = participants.length + 1;

    let videoCount = localVideoTrack ? 1 : 0;
    let audioCount = 0;

    participants.forEach((participant) => {
        participant.tracks.forEach((pub) => {
            if (pub.kind === Track.Kind.Video) videoCount++;
            if (pub.kind === Track.Kind.Audio) audioCount++;
        });
    });

    elements.videoCount.textContent = videoCount;
    elements.audioCount.textContent = audioCount;
}

function updateParticipantsList() {
    if (!room || !room.participants) {
        elements.participantsList.innerHTML =
            '<div style="color: #aaa; text-align: center;">참가자 없음</div>';
        return;
    }

    const participants = Array.from(room.participants.values());

    if (participants.length === 0) {
        elements.participantsList.innerHTML =
            '<div style="color: #aaa; text-align: center;">다른 참가자 없음</div>';
        return;
    }

    elements.participantsList.innerHTML = participants
        .map(
            (p) => `
        <div class="participant-item">
            <span class="participant-name">${p.identity}</span>
            <span class="participant-role">${p.metadata || "student"}</span>
        </div>
    `,
        )
        .join("");
}

async function getToken(nodeUrl, userId, roomName, userType) {
    const url = `${nodeUrl}/api/livekit/token?user_id=${userId}&room_name=${roomName}&user_type=${userType}`;
    log(`토큰 요청: ${url}`);

    const response = await fetch(url, { method: "POST" });
    if (!response.ok) {
        const errorText = await response.text();
        throw new Error(
            `Token request failed (${response.status}): ${errorText}`,
        );
    }

    const data = await response.json();
    log(`✅ 토큰 발급 성공`);
    log(`  📍 LiveKit URL: ${data.url}`);
    log(`  🎯 Room: ${data.room_name}`);
    log(`  👤 User: ${data.identity} (${data.user_type})`);

    return data;
}

async function disconnect() {
    try {
        if (room) {
            room.disconnect();
            room = null;
        }
        updateStatus("disconnected", "연결 해제됨");
        elements.connectBtn.disabled = false;
        elements.disconnectBtn.disabled = true;
        elements.shareBtn.disabled = true;
        elements.localVideo.srcObject = null;
        elements.videoGrid.innerHTML = "";
        elements.participantsList.innerHTML =
            '<div style="color: #aaa; text-align: center;">참가자 없음</div>';
        elements.videoCount.textContent = "0";
        elements.audioCount.textContent = "0";
        log("✅ 연결 해제 완료");
    } catch (error) {
        console.error("연결 해제 실패:", error);
        log(`❌ 연결 해제 실패: ${error.message}`);
    }
}

async function shareScreen() {
    try {
        if (!room) {
            log("❌ 먼저 연결해주세요");
            return;
        }

        log("🔄 화면 공유 시작 중...");

        const { LocalVideoTrack, Track } = LivekitClient;

        // 1. 4K 120fps를 위한 커스텀 프리셋 정의 (일반 객체 사용)
        const HighFPSPreset = {
            width: 3840,
            height: 2160,
            maxBitrate: 60_000_000,
            maxFramerate: 120
        };

        const stream = await navigator.mediaDevices.getDisplayMedia({
            video: {
                width: { ideal: 3840, max: 3840 },
                height: { ideal: 2160, max: 2160 },
                frameRate: { ideal: 120, max: 120 }
            },
            audio: false
        });

        const videoTrack = stream.getVideoTracks()[0];
        const settings = videoTrack.getSettings();
        
        log("✅ 화면 공유 시작 완료");
        log("=== 📊 캡처된 트랙 설정 ==>");
        log(`  해상도: ${settings.width}x${settings.height}`);
        log(`  FPS: ${settings.frameRate}`);

        const track = new LocalVideoTrack(videoTrack, undefined, false, {
            simulcast: false,
            videoEncoding: {
                maxBitrate: HighFPSPreset.maxBitrate,
                maxFramerate: HighFPSPreset.maxFramerate
            }
        });

        // 120fps 부드러운 움직임 최적화
        if (videoTrack.contentHint !== 'motion') {
            videoTrack.contentHint = 'motion';
        }

        await room.localParticipant.publishTrack(track, {
            source: Track.Source.ScreenShare,
            videoCodec: 'h264', // H.264 하드웨어 가속 사용
            videoEncoding: {
                maxBitrate: HighFPSPreset.maxBitrate,
                maxFramerate: HighFPSPreset.maxFramerate
            },
            screenShareEncoding: {
                maxBitrate: HighFPSPreset.maxBitrate,
                maxFramerate: HighFPSPreset.maxFramerate
            },
            simulcast: false, // 단일 고화질 스트림 강제
            degradationPreference: 'balanced' // 해상도와 프레임 균형 유지
        });

        localVideoTrack = track;
        updateStats();

        elements.localVideo.srcObject = stream;

        videoTrack.addEventListener("ended", () => {
            log("화면 공유가 종료되었습니다");
            track.stop();
            room.localParticipant.unpublishTrack(track);
            localVideoTrack = null;
            updateStats();
        });
    } catch (error) {
        log(`❌ 화면 공유 실패: ${error.message}`);
        console.error("화면 공유 실패:", error);
    }
}

async function connect() {
    try {
        updateStatus("connecting", "연결 중...");
        elements.connectBtn.disabled = true;

        const nodeUrl = elements.nodeSelect.value;
        const userId = elements.userId.value || `user-${Date.now()}`;
        const roomName = elements.roomName.value;
        const userType = elements.userType.value;

        log(`연결 시작: ${nodeUrl} (${userId})`);

        const tokenData = await getToken(nodeUrl, userId, roomName, userType);

        const { Room, RoomEvent, Track, VideoPresets, VideoQuality } = LivekitClient;

        room = new Room({
            adaptiveStream: false,
            dynacast: false,
            videoCaptureDefaults: {
                resolution: VideoPresets.h2160.resolution,
                frameRate: 120,
            },
            publishDefaults: {
                videoCodec: "h264",
                simulcast: false,
                degradationPreference: "balanced",
                videoEncoding: {
                    maxBitrate: 60_000_000,
                    maxFramerate: 120,
                    priority: "high",
                },
            },
        });

        room.on(RoomEvent.ParticipantConnected, (participant) => {
            log(`✅ 참가자 연결: ${participant.identity}`);
            updateStats();
            updateParticipantsList();
        });

        room.on(RoomEvent.ParticipantDisconnected, (participant) => {
            log(`❌ 참가자 연결 해제: ${participant.identity}`);
            updateStats();
            updateParticipantsList();
        });

        room.on(RoomEvent.TrackSubscribed, (track, publication, participant) => {
            log(`📬 트랙 구독: ${track.kind} from ${participant.identity}`);
            if (track.kind === Track.Kind.Video) {
                publication.setVideoQuality(VideoQuality.HIGH);
                publication.setVideoDimensions({ width: 3840, height: 2160 });
                
                const videoElement = track.attach();
                videoElement.style.width = '100%';
                videoElement.style.height = 'auto';
                videoElement.style.objectFit = 'contain';
                
                const container = document.createElement('div');
                container.className = 'video-container';
                const label = document.createElement('div');
                label.className = 'video-label';
                label.textContent = participant.identity;
                container.appendChild(label);
                container.appendChild(videoElement);
                elements.videoGrid.appendChild(container);
                
                log(`📺 비디오 수신 화질: HIGH (3840x2160 요청)`);
            }
            updateStats();
        });

        await room.connect(tokenData.url, tokenData.token);
        log("✅ LiveKit 연결 완료");
        updateStatus("connected", "연결됨");
        elements.disconnectBtn.disabled = false;
        elements.shareBtn.disabled = false;
        updateStats();
        updateParticipantsList();
    } catch (error) {
        console.error("연결 실패:", error);
        log(`❌ 연결 실패: ${error.message}`);
        updateStatus("disconnected", "연결 실패");
        elements.connectBtn.disabled = false;
    }
}

function initializeLiveKit() {
    LivekitClient = window.LivekitClient;
    const { setLogLevel, version } = LivekitClient;
    
    setLogLevel("debug");
    console.log("🔧 LiveKit SDK debug logging enabled");
    console.log("LiveKit Client SDK version:", version || "unknown");

    initElements();

    elements.connectBtn.addEventListener("click", connect);
    elements.disconnectBtn.addEventListener("click", disconnect);
    elements.shareBtn.addEventListener("click", shareScreen);

    elements.userType.addEventListener("change", (e) => {
        const type = e.target.value;
        elements.userId.value = `${type}-${Math.random().toString(36).substr(2, 6)}`;
    });

    elements.userId.value = `teacher-${Math.random().toString(36).substr(2, 6)}`;

    log("✅ LiveKit 클라이언트 준비 완료");
    log("💡 연결하기 버튼을 클릭하여 시작하세요");
}

window.addEventListener("load", () => {
    if (!window.LivekitClient) {
        console.error("LiveKit SDK not loaded");
        return;
    }
    initializeLiveKit();
});
