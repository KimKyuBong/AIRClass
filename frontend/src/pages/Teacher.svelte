<script>
  import { onMount, onDestroy, tick } from 'svelte';
  import { slide } from 'svelte/transition';
  import { Room, RoomEvent, Track } from 'livekit-client';
  import 'vidstack/player';
  import 'vidstack/player/ui';
  import 'vidstack/player/layouts/default';
  import 'vidstack/icons';

  let ws = null;
  let mediaPlayerEl = null;
  let livekitRoom = null;
  let isConnected = false;
  let isVideoLoaded = false;
  let students = [];
  let messages = [];
  let newMessage = '';
  let latencyMonitorInterval = null;
  let currentLatency = 0;
  
  // WebRTC viewer tracking
  let viewers = [];
  let viewerCount = 0;
  let viewerPollInterval = null;
  let streamReady = false;
  let nodeStats = {};
  let clusterMode = 'unknown';

  let isBroadcasting = false;
  let broadcastStream = null;
  let videoContainer = null; // 전체화면용 컨테이너
  let isFullscreen = false;
  let isPip = false;

  // 스트림 소스 관리
  let streamSource = 'android'; // 'android' | 'pc'
  let isSourceSwitching = false;

  // Gemini AI State
  let geminiStatus = { enabled: false, env_fallback_available: false };
  let geminiKeyInput = '';
  let geminiTestPrompt = '';
  let geminiTestResponse = '';
  let isGeminiLoading = false;
  let geminiError = '';
  let aiEnabled = false;
  let showSettings = false;
  let geminiNotice = '';
  let activeTab = 'chat'; // 'chat' | 'viewers' | 'ai'

  // Screen Share Settings
  let showScreenSettings = false;
  let screenResolution = '3840x2160';
  let screenFps = 120;
  let screenBitrate = 60; // Mbps
  /** @type {'vp9' | 'h264' | 'av1' | 'vp8' | 'h265'} */
  let screenCodec = 'vp9';
  let screenContentHint = 'motion';

  const resolutionOptions = [
    { value: '1920x1080', label: '1920×1080 (Full HD)' },
    { value: '2560x1440', label: '2560×1440 (2K)' },
    { value: '3840x2160', label: '3840×2160 (4K)' }
  ];

  const fpsOptions = [
    { value: 30, label: '30 FPS' },
    { value: 60, label: '60 FPS' },
    { value: 120, label: '120 FPS' }
  ];

  const codecOptions = [
    { value: 'h264', label: 'H.264 (Compatible)' },
    { value: 'vp9', label: 'VP9 (Recommended)' },
    { value: 'av1', label: 'AV1 (Experimental)' }
  ];

  const contentHintOptions = [
    { value: 'detail', label: 'Detail (High Quality)' },
    { value: 'motion', label: 'Motion (Smooth)' },
    { value: 'text', label: 'Text (Crisp)' }
  ];

  onMount(async () => {
    console.log('[Teacher] Component mounted');
    document.addEventListener('fullscreenchange', onFullscreenChange);
    document.addEventListener('pictureinpicturechange', onPipChange);

    fetchGeminiStatus();
    
    window.onerror = function(msg, url, line, col, error) {
      alert(`💥 GLOBAL ERROR 💥\n\nMsg: ${msg}\nLine: ${line}:${col}\nError: ${error ? error.stack : 'N/A'}`);
      return false;
    };

    connectWebSocket();
    streamSource = 'android';
    await fetchTokenAndInitWebRTC();
    startViewerPolling();
  });

  onDestroy(() => {
    document.removeEventListener('fullscreenchange', onFullscreenChange);
    document.removeEventListener('pictureinpicturechange', onPipChange);
    if (document.fullscreenElement) document.exitFullscreen();
    if (document.pictureInPictureElement) document.exitPictureInPicture();
    if (livekitRoom) {
      livekitRoom.disconnect();
    }
    if (viewerPollInterval) {
      clearInterval(viewerPollInterval);
    }
    if (latencyMonitorInterval) {
      clearInterval(latencyMonitorInterval);
    }
    if (ws) {
      ws.close();
    }
  });

  function handleBroadcastToggle() {
    try {
      if (isBroadcasting) {
        stopBroadcast();
      } else {
        startBroadcast();
      }
    } catch (e) {
      alert(`핸들러 실행 중 에러: ${e.message}`);
    }
  }

  function startLatencyMonitoringFromContainer() {
    setTimeout(() => {
      const v = videoContainer?.querySelector?.('video');
      if (v) startLatencyMonitoring(v);
    }, 300);
  }

  async function startBroadcast() {
    try {
      if (isBroadcasting) return;

      if (!navigator.mediaDevices || !navigator.mediaDevices.getDisplayMedia) {
        throw new Error(
          '브라우저가 화면 공유를 지원하지 않습니다.\n(원인: HTTPS가 아니거나 localhost가 아님)\n현재 주소: ' + window.location.href
        );
      }
      
      console.log('[Teacher] Starting broadcast...');
      
      // 1. Get Display Media with UI settings
      try {
        const [width, height] = screenResolution.split('x').map(Number);
        
        broadcastStream = await navigator.mediaDevices.getDisplayMedia({
          video: {
            width: { ideal: width, max: width },
            height: { ideal: height, max: height },
            frameRate: { ideal: screenFps, max: screenFps }
          },
          audio: true
        });
      } catch (e) {
        if (e.name === 'NotAllowedError') {
          console.log('User cancelled screen share');
          return;
        }
        throw new Error(`화면 선택 실패: ${e.name} - ${e.message}`);
      }
      
      // 2. Get LiveKit token from backend
      console.log('[Teacher] Fetching LiveKit token...');
      const response = await fetch(`/api/livekit/token?user_id=Teacher&room_name=class&user_type=teacher&emulator=true`, { method: 'POST' });
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`토큰 발급 실패: ${errorText}`);
      }
      const { token, url } = await response.json();
      
      // 3. Connect to LiveKit room with high-performance defaults
      if (livekitRoom) {
        await livekitRoom.disconnect();
        livekitRoom = null;
        await new Promise((r) => setTimeout(r, 150));
      }
      livekitRoom = new Room({
        adaptiveStream: false,
        dynacast: false,
        publishDefaults: {
          simulcast: false,
          videoCodec: screenCodec,
          videoEncoding: {
            maxBitrate: screenBitrate * 1_000_000,
            maxFramerate: screenFps,
            priority: 'high'
          },
          screenShareEncoding: {
            maxBitrate: screenBitrate * 1_000_000,
            maxFramerate: screenFps,
            priority: 'high'
          }
        }
      });
      await livekitRoom.connect(url, token);
      
      // 4. Apply contentHint for motion optimization
      const videoTrack = broadcastStream.getVideoTracks()[0];
      const audioTrack = broadcastStream.getAudioTracks()[0];
      
      if (screenContentHint) {
        videoTrack.contentHint = screenContentHint;
      }
      
      // 5. Publish tracks with explicit high-quality settings
      await livekitRoom.localParticipant.publishTrack(videoTrack, {
        source: Track.Source.ScreenShare,
        simulcast: false,
        videoCodec: screenCodec,
        videoEncoding: {
          maxBitrate: screenBitrate * 1_000_000,
          maxFramerate: screenFps
        },
        screenShareEncoding: {
          maxBitrate: screenBitrate * 1_000_000,
          maxFramerate: screenFps
        }
      });
      if (audioTrack) await livekitRoom.localParticipant.publishTrack(audioTrack);

      broadcastStream.getVideoTracks()[0].onended = () => {
        console.log('[Teacher] User stopped screen share via browser UI');
        stopBroadcast();
      };
      
      isBroadcasting = true;
      isVideoLoaded = true;
      
    } catch (error) {
      console.error('[Teacher] Broadcast failed:', error);
      stopBroadcast();
      
      const errorDump = [
        `Message: ${error.message}`,
        `Name: ${error.name}`,
        `Stack: ${error.stack || 'N/A'}`
      ].filter(Boolean).join('\n\n');

      alert(`🚨 CRITICAL ERROR 🚨\n\n${errorDump}`);
    }
  }

  async function stopBroadcast() {
    if (!isBroadcasting && !broadcastStream && !livekitRoom) return;
    
    console.log('[Teacher] Stopping broadcast...');
    
    if (livekitRoom) {
      await livekitRoom.disconnect();
      livekitRoom = null;
    }

    if (broadcastStream) {
      broadcastStream.getTracks().forEach(track => track.stop());
      broadcastStream = null;
    }

    if (latencyMonitorInterval) {
      clearInterval(latencyMonitorInterval);
      latencyMonitorInterval = null;
    }
    currentLatency = 0;
    
    isBroadcasting = false;
    isVideoLoaded = false;
    
    console.log('[Teacher] Reverting to Android viewer mode...');
    streamSource = 'android';
    await fetchTokenAndInitWebRTC();
  }

  async function switchStreamSource(newSource) {
    if (isSourceSwitching) return;
    if (streamSource === newSource && !isBroadcasting) return;
    
    isSourceSwitching = true;
    console.log(`[Teacher] Switching stream source from ${streamSource} to ${newSource}`);
    
    try {
      if (isBroadcasting) {
        await stopBroadcast();
      } else if (livekitRoom) {
        await livekitRoom.disconnect();
        livekitRoom = null;
        await new Promise((r) => setTimeout(r, 150));
      }
      
      if (latencyMonitorInterval) {
        clearInterval(latencyMonitorInterval);
        latencyMonitorInterval = null;
      }
      currentLatency = 0;

      isVideoLoaded = false;
      broadcastStream = null;
      streamSource = newSource;
      
      if (newSource === 'android') {
        await fetchTokenAndInitWebRTC();
      } else if (newSource === 'pc') {
        await startBroadcast();
      }
    } catch (error) {
      console.error('[Teacher] Error switching stream source:', error);
      alert(`소스 전환 실패: ${error.message}`);
      streamSource = 'android';
      await fetchTokenAndInitWebRTC();
    } finally {
      isSourceSwitching = false;
    }
  }

  async function fetchTokenAndInitWebRTC() {
    if (isBroadcasting) return;

    try {
      console.log('[Teacher] Fetching LiveKit token for viewer mode...');
      const response = await fetch(`/api/livekit/token?user_id=Teacher&room_name=class&user_type=teacher&emulator=true`, { method: 'POST' });
      if (!response.ok) throw new Error('Failed to get token');
      
      const { token, url } = await response.json();
      
      if (livekitRoom) {
        await livekitRoom.disconnect();
        livekitRoom = null;
        await new Promise((r) => setTimeout(r, 150));
      }
      
      livekitRoom = new Room();
      await livekitRoom.connect(url, token);
      console.log('[Teacher] Connected to LiveKit room');
      
      livekitRoom.on(RoomEvent.TrackSubscribed, (track, publication, participant) => {
        console.log('[Teacher] Track subscribed:', track.kind, 'from', participant.identity);
        if (track.kind === 'video') {
          broadcastStream = new MediaStream([track.mediaStreamTrack]);
          isVideoLoaded = true;
          startLatencyMonitoringFromContainer();
        }
      });

      // Handle existing tracks
      livekitRoom.remoteParticipants.forEach(participant => {
        participant.trackPublications.forEach(publication => {
          if (publication.isSubscribed && publication.track?.kind === 'video') {
            broadcastStream = new MediaStream([publication.track.mediaStreamTrack]);
            isVideoLoaded = true;
            startLatencyMonitoringFromContainer();
          }
        });
      });
      
    } catch (error) {
      console.error('[Teacher] LiveKit connection error:', error);
    }
  }

  function startLatencyMonitoring(video) {
    if (latencyMonitorInterval) clearInterval(latencyMonitorInterval);
    latencyMonitorInterval = setInterval(() => {
      if (video && video.buffered && video.buffered.length > 0) {
        const currentTime = video.currentTime;
        const bufferedEnd = video.buffered.end(video.buffered.length - 1);
        const lag = bufferedEnd - currentTime;
        currentLatency = Math.max(0, Math.round(lag * 1000));
        
        if (lag > 0.2) {
          video.currentTime = bufferedEnd - 0.02;
        }
      }
    }, 100);
  }

  function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${window.location.host}/ws/teacher`);
    
    ws.onopen = () => {
      isConnected = true;
      console.log('Teacher WebSocket connected');
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'student_list') {
        students = data.students.map(name => ({
          name: name,
          joinedAt: new Date().toLocaleTimeString('ko-KR')
        }));
      } else if (data.type === 'chat') {
        messages = [...messages, {
          sender: data.from,
          text: data.message
        }];
      }
    };

    ws.onclose = () => {
      isConnected = false;
      setTimeout(connectWebSocket, 3000);
    };
  }

  function sendMessage() {
    if (newMessage.trim() && ws) {
      ws.send(JSON.stringify({
        type: 'chat',
        message: newMessage
      }));
      newMessage = '';
    }
  }
  
  function startViewerPolling() {
    fetchViewers();
    viewerPollInterval = setInterval(async () => {
      await fetchViewers();
    }, 2000);
  }
  
  async function fetchViewers() {
    try {
      const response = await fetch(`/api/viewers`);
      if (response.ok) {
        const data = await response.json();
        viewerCount = data.total_viewers || 0;
        viewers = data.viewers || [];
        streamReady = data.stream_ready || false;
        nodeStats = data.node_stats || {};
        clusterMode = data.cluster_mode || 'unknown';
      }
    } catch (error) {
      console.error('[Teacher] Error fetching viewers:', error);
    }
  }

  async function fetchGeminiStatus() {
    try {
      const res = await fetch(`/api/ai/keys/gemini/status?teacher_id=Teacher`);
      if (res.ok) {
        const data = await res.json();
        geminiStatus = {
          enabled: !!data.enabled,
          env_fallback_available: !!data.env_fallback_available
        };
        if (geminiStatus.enabled || geminiStatus.env_fallback_available) {
          aiEnabled = true;
        }
      } else {
        geminiStatus = { enabled: false, env_fallback_available: false };
      }
    } catch (e) {
      console.warn('Gemini status unavailable:', e);
      geminiStatus = { enabled: false, env_fallback_available: false };
    }
  }

  async function saveGeminiKey() {
    if (!geminiKeyInput.trim()) return;
    isGeminiLoading = true;
    geminiError = '';
    geminiNotice = '';
    try {
      const res = await fetch(`/api/ai/keys/gemini?teacher_id=Teacher&api_key=${encodeURIComponent(geminiKeyInput)}`, {
        method: 'POST'
      });
      if (!res.ok) throw new Error(await res.text());
      geminiKeyInput = '';
      await fetchGeminiStatus();
      geminiNotice = "✅ 키가 안전하게 저장되었습니다.";
      showSettings = false;
    } catch (e) {
      geminiError = e.message;
    } finally {
      isGeminiLoading = false;
    }
  }

  async function deleteGeminiKey() {
    if (!confirm('Gemini 키를 삭제하시겠습니까?')) return;
    isGeminiLoading = true;
    geminiError = '';
    geminiNotice = '';
    try {
      const res = await fetch(`/api/ai/keys/gemini?teacher_id=Teacher`, {
        method: 'DELETE'
      });
      if (!res.ok) throw new Error(await res.text());
      await fetchGeminiStatus();
      geminiNotice = "🗑️ 키가 삭제되었습니다.";
      geminiTestResponse = '';
    } catch (e) {
      geminiError = e.message;
    } finally {
      isGeminiLoading = false;
    }
  }

  function onFullscreenChange() {
    isFullscreen = !!document.fullscreenElement;
  }
  function onPipChange() {
    isPip = !!document.pictureInPictureElement;
  }

  async function toggleFullscreen() {
    if (!videoContainer) return;
    try {
      if (document.fullscreenElement) {
        await document.exitFullscreen();
        isFullscreen = false;
      } else {
        await videoContainer.requestFullscreen();
        isFullscreen = true;
      }
    } catch (e) {
      console.warn('Fullscreen error:', e);
    }
  }

  async function togglePip() {
    try {
      if (document.pictureInPictureElement) {
        await document.exitPictureInPicture();
        isPip = false;
        return;
      }
      const player = mediaPlayerEl ?? videoContainer?.querySelector?.('media-player');
      const video = videoContainer?.querySelector?.('video');
      if (player && typeof player.enterPictureInPicture === 'function') {
        await player.enterPictureInPicture();
        isPip = true;
      } else if (video) {
        await video.requestPictureInPicture();
        isPip = true;
      }
    } catch (e) {
      console.warn('PIP error:', e);
    }
  }

  async function testGemini() {
    if (!geminiTestPrompt.trim()) return;
    isGeminiLoading = true;
    geminiError = '';
    geminiTestResponse = '';
    geminiNotice = '';
    try {
      const res = await fetch(`/api/ai/gemini/generate?teacher_id=Teacher&model=gemini-1.5-flash&prompt=${encodeURIComponent(geminiTestPrompt)}`, {
        method: 'POST'
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      geminiTestResponse = data.text;
    } catch (e) {
      geminiError = e.message;
    } finally {
      isGeminiLoading = false;
    }
  }
</script>

<style>
  /* 전체화면: 화면 전체 채우고 비디오는 contain으로 전부 보이기 (검은 화면 방지) */
  :global(.video-container:fullscreen) {
    width: 100vw !important;
    height: 100vh !important;
    background: black !important;
    display: flex !important;
    justify-content: center !important;
    align-items: center !important;
    aspect-ratio: unset !important;
  }
  :global(.video-container:fullscreen .video-container-inner) {
    width: 100% !important;
    height: 100% !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    background: black !important;
  }
  :global(.video-container:fullscreen .video-container-inner media-player) {
    width: 100% !important;
    height: 100% !important;
    display: block !important;
  }
  :global(.video-container:fullscreen .video-container-inner video),
  :global(.video-container:fullscreen) video {
    width: 100% !important;
    height: 100% !important;
    object-fit: contain !important;
  }
</style>

<div class="min-h-screen bg-gray-50">
  <!-- Header -->
  <header class="bg-white border-b border-gray-200 px-6 py-4 shadow-sm">
    <div class="flex items-center justify-between max-w-7xl mx-auto">
      <div class="flex items-center gap-3">
        <div class="w-3 h-3 rounded-full {isConnected ? 'bg-green-500' : 'bg-red-500'}"></div>
        <h1 class="text-2xl font-bold text-gray-800">👨‍🏫 AIRClass Teacher</h1>
        {#if currentLatency > 0}
          <span class="text-xs px-2 py-1 rounded {currentLatency < 300 ? 'bg-green-100 text-green-800' : currentLatency < 1000 ? 'bg-yellow-100 text-yellow-800' : 'bg-red-100 text-red-800'}">
            {currentLatency}ms
          </span>
        {/if}
      </div>
      <div class="flex items-center gap-4">
        <!-- 스트림 소스 선택 -->
        <div class="flex items-center gap-2 bg-gray-100 rounded-lg p-1">
          <button
            on:click={() => switchStreamSource('android')}
            disabled={isSourceSwitching}
            class="px-3 py-1.5 rounded-md font-medium transition-all text-sm {streamSource === 'android' && !isBroadcasting ? 'bg-white text-blue-600 shadow-sm' : 'text-gray-600 hover:text-gray-900'} {isSourceSwitching ? 'opacity-50 cursor-not-allowed' : ''}"
          >
            📱 Android 앱
          </button>
          <button
            on:click={() => switchStreamSource('pc')}
            disabled={isSourceSwitching}
            class="px-3 py-1.5 rounded-md font-medium transition-all text-sm {streamSource === 'pc' || isBroadcasting ? 'bg-white text-blue-600 shadow-sm' : 'text-gray-600 hover:text-gray-900'} {isSourceSwitching ? 'opacity-50 cursor-not-allowed' : ''}"
          >
            🖥️ PC 화면
          </button>
        </div>
        
        <!-- PC 화면 공유 중지 버튼 (PC 모드일 때만 표시) -->
        {#if isBroadcasting}
          <button
            on:click={handleBroadcastToggle}
            class="px-4 py-2 rounded-lg font-medium transition-colors text-sm bg-red-500 text-white hover:bg-red-600"
          >
            ⏹️ 공유 중지
          </button>
        {/if}
        
        <div class="text-sm text-gray-600">
          실시간 시청자 {viewerCount}명
        </div>
        <div class="text-xs text-green-600 font-semibold">
          WebRTC 초저지연
        </div>
      </div>
    </div>
  </header>

  <main class="max-w-7xl mx-auto p-6">
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Screen Preview -->
      <div class="lg:col-span-2">
        <div class="bg-white rounded-lg shadow p-4">
          <h2 class="text-lg font-semibold mb-4 text-gray-800 flex items-center gap-2">
            {#if isBroadcasting}
              <span class="text-red-600">🔴</span> PC 화면 송출 중 (WebRTC)
            {:else if streamSource === 'android'}
              <span class="text-blue-600">📱</span> Android 스트림 미리보기
            {:else}
              <span class="text-gray-600">🖥️</span> 스트림 미리보기
            {/if}
          </h2>
          <div
            bind:this={videoContainer}
            class="bg-black rounded-lg aspect-video flex items-center justify-center overflow-hidden relative video-container"
          >
            <div class="video-container-inner w-full h-full min-w-0 min-h-0">
              {#if broadcastStream}
                <media-player
                  bind:this={mediaPlayerEl}
                  src={{ src: broadcastStream, type: 'video/object' }}
                  autoplay
                  muted
                  playsinline
                  class="w-full h-full"
                >
                  <media-provider></media-provider>
                  <media-video-layout></media-video-layout>
                </media-player>
              {/if}
            </div>

            <!-- PIP / 전체화면 버튼 -->
            {#if isVideoLoaded}
              <div class="absolute bottom-3 right-3 z-40 flex gap-2">
                <button
                  type="button"
                  on:click={togglePip}
                  class="p-2 rounded-lg bg-black/60 text-white hover:bg-black/80 transition"
                  title="작은 창 (PIP)"
                >
                  <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M19 7h-8v6h8V7zm2-4H3c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h18c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H3V5h18v14z"/></svg>
                </button>
                <button
                  type="button"
                  on:click={toggleFullscreen}
                  class="p-2 rounded-lg bg-black/60 text-white hover:bg-black/80 transition"
                  title="전체화면"
                >
                  {#if isFullscreen}
                    <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M5 16h3v3h2v-5H5v2zm3-8H5v2h5V5H8v3zm6 11h2v-3h3v-2h-5v5zm2-11V5h-2v5h5V8h-3z"/></svg>
                  {:else}
                    <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M7 14H5v5h5v-2H7v-3zm-2-4h2V7h3V5H5v5zm12 7h-3v2h5v-5h-2v3zM14 5v2h3v3h2V5h-5z"/></svg>
                  {/if}
                </button>
              </div>
            {/if}
            
            {#if !isVideoLoaded}
              <div class="absolute inset-0 flex items-center justify-center text-center text-gray-400 bg-gray-900 bg-opacity-90">
                <div>
                  {#if isSourceSwitching}
                    <div class="text-4xl mb-2">⏳</div>
                    <p>소스 전환 중...</p>
                  {:else if streamSource === 'android'}
                    <div class="text-4xl mb-2">📱</div>
                    <p>Android 앱에서 화면 공유 시작</p>
                    <p class="text-sm mt-4 text-gray-500">
                      RTMP URL: rtmp://서버IP:1935/live/stream
                    </p>
                    <p class="text-xs mt-4 text-gray-500">
                      또는 위의 "🖥️ PC 화면" 버튼을 눌러 PC 화면을 공유하세요
                    </p>
                  {:else if streamSource === 'pc'}
                    <div class="text-4xl mb-2">🖥️</div>
                    <p>PC 화면 공유 준비 중...</p>
                    <p class="text-xs mt-4 text-gray-500">화면 선택 창이 나타납니다</p>
                  {/if}
                </div>
              </div>
            {/if}
          </div>
        </div>

        <!-- WebRTC Viewer List -->
        <div class="bg-white rounded-lg shadow p-4 mt-6">
          <h2 class="text-lg font-semibold mb-4 text-gray-800">
            실시간 시청자 ({viewerCount}명)
            {#if streamReady}
              <span class="text-xs text-green-600 ml-2">● 스트림 활성</span>
            {:else}
              <span class="text-xs text-gray-400 ml-2">○ 스트림 대기중</span>
            {/if}
          </h2>
          <div class="space-y-2">
            {#each viewers as viewer}
              <div class="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                <div class="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                <span class="text-sm text-gray-700">WebRTC 시청자</span>
                <span class="text-xs px-2 py-1 bg-blue-100 text-blue-700 rounded">
                  {viewer.node || 'main'}
                </span>
                <span class="text-xs text-gray-500 ml-auto">
                  {new Date(viewer.connected_at).toLocaleTimeString('ko-KR')}
                </span>
              </div>
            {:else}
              <p class="text-sm text-gray-500 text-center py-4">접속 중인 시청자가 없습니다</p>
            {/each}
          </div>
        </div>

        <!-- Node Load Statistics -->
        {#if Object.keys(nodeStats).length > 0}
          <div class="bg-white rounded-lg shadow p-4 mt-6">
            <h2 class="text-lg font-semibold mb-4 text-gray-800">
              클러스터 노드 부하율
              <span class="text-xs text-gray-500 ml-2">({clusterMode} mode)</span>
            </h2>
            <div class="space-y-3">
              {#each Object.values(nodeStats) as node}
                <div class="border-l-4 pl-4 py-2 {node.load_percent > 80 ? 'border-red-500' : node.load_percent > 50 ? 'border-yellow-500' : 'border-green-500'}">
                  <div class="flex items-center justify-between mb-2">
                    <div class="flex items-center gap-2">
                      <span class="font-semibold text-gray-800">{node.name}</span>
                      <span class="text-xs px-2 py-1 rounded {node.status === 'active' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'}">
                        {node.status}
                      </span>
                    </div>
                    <span class="text-sm font-bold {node.load_percent > 80 ? 'text-red-600' : node.load_percent > 50 ? 'text-yellow-600' : 'text-green-600'}">
                      {node.load_percent}%
                    </span>
                  </div>
                  
                  <!-- Progress Bar -->
                  <div class="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
                    <div 
                      class="h-2 rounded-full transition-all duration-300 {node.load_percent > 80 ? 'bg-red-500' : node.load_percent > 50 ? 'bg-yellow-500' : 'bg-green-500'}"
                      style="width: {node.load_percent}%"
                    ></div>
                  </div>
                  
                  <div class="flex items-center justify-between mt-1 text-xs text-gray-600">
                    <span>{node.viewers} / {node.capacity} 시청자</span>
                    {#if node.webrtc_port && node.webrtc_port !== 'unknown'}
                      <span class="text-gray-400">Port: {node.webrtc_port}</span>
                    {/if}
                  </div>
                </div>
              {/each}
            </div>
          </div>
        {/if}
      </div>

      <div class="lg:col-span-1 flex flex-col gap-6">
        
        <!-- Screen Share Settings Panel -->
        <div class="bg-white rounded-lg shadow p-4 border border-purple-100 transition-all duration-300">
          <div class="flex items-center justify-between mb-4">
            <h2 class="text-lg font-bold text-gray-800 flex items-center gap-2">
              🎥 화면 공유 설정
            </h2>
            <button
              on:click={() => showScreenSettings = !showScreenSettings}
              class="p-2 rounded-lg transition-colors {showScreenSettings ? 'bg-purple-100 text-purple-600' : 'text-gray-500 hover:bg-gray-100'}"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </button>
          </div>

          {#if showScreenSettings}
            <div transition:slide class="space-y-3">
              <!-- Resolution -->
              <div>
                <label class="block text-xs font-semibold text-gray-600 mb-1.5 uppercase tracking-wide">
                  해상도
                </label>
                <select bind:value={screenResolution} class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 bg-white">
                  {#each resolutionOptions as option}
                    <option value={option.value}>{option.label}</option>
                  {/each}
                </select>
              </div>

              <!-- FPS -->
              <div>
                <label class="block text-xs font-semibold text-gray-600 mb-1.5 uppercase tracking-wide">
                  프레임레이트
                </label>
                <select bind:value={screenFps} class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 bg-white">
                  {#each fpsOptions as option}
                    <option value={option.value}>{option.label}</option>
                  {/each}
                </select>
              </div>

              <!-- Bitrate -->
              <div>
                <label class="block text-xs font-semibold text-gray-600 mb-1.5 uppercase tracking-wide">
                  비트레이트 (Mbps)
                </label>
                <input
                  type="number"
                  bind:value={screenBitrate}
                  min="1"
                  max="100"
                  step="1"
                  class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 bg-white"
                />
              </div>

              <!-- Codec -->
              <div>
                <label class="block text-xs font-semibold text-gray-600 mb-1.5 uppercase tracking-wide">
                  코덱
                </label>
                <select bind:value={screenCodec} class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 bg-white">
                  {#each codecOptions as option}
                    <option value={option.value}>{option.label}</option>
                  {/each}
                </select>
              </div>

              <!-- Content Hint -->
              <div>
                <label class="block text-xs font-semibold text-gray-600 mb-1.5 uppercase tracking-wide">
                  최적화 모드
                </label>
                <select bind:value={screenContentHint} class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 bg-white">
                  {#each contentHintOptions as option}
                    <option value={option.value}>{option.label}</option>
                  {/each}
                </select>
              </div>

              <!-- Current Settings Display -->
              <div class="mt-4 p-3 bg-purple-50 border border-purple-200 rounded-lg">
                <p class="text-xs font-semibold text-purple-800 mb-2">현재 설정</p>
                <p class="text-xs text-purple-700">
                  {screenResolution.replace('x', '×')} • {screenFps} FPS • {screenBitrate} Mbps • {screenCodec.toUpperCase()}
                </p>
              </div>
            </div>
          {/if}
        </div>
        
        <div class="bg-white rounded-lg shadow p-4 border border-blue-100 transition-all duration-300">
          <div class="flex items-center justify-between mb-4">
            <h2 class="text-lg font-bold text-gray-800 flex items-center gap-2">
              ✨ Gemini AI
            </h2>
            <div class="flex items-center gap-3">
              <label class="relative inline-flex items-center cursor-pointer">
                <input type="checkbox" bind:checked={aiEnabled} class="sr-only peer">
                <div class="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-100 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                <span class="ml-2 text-sm font-medium text-gray-600">{aiEnabled ? 'ON' : 'OFF'}</span>
              </label>
            </div>
          </div>

          <!-- Status Bar -->
          <div class="flex items-center gap-2 mb-4">
             {#if geminiStatus.enabled}
                <span class="text-xs px-2.5 py-0.5 bg-green-100 text-green-700 rounded-full border border-green-200 font-medium">Active</span>
              {:else if geminiStatus.env_fallback_available}
                <span class="text-xs px-2.5 py-0.5 bg-blue-100 text-blue-700 rounded-full border border-blue-200 font-medium">System Key</span>
              {:else}
                <span class="text-xs px-2.5 py-0.5 bg-gray-100 text-gray-600 rounded-full border border-gray-200 font-medium">Inactive</span>
              {/if}
              
              <button 
                on:click={fetchGeminiStatus} 
                class="p-1 hover:bg-gray-100 rounded-full text-gray-500 transition-colors"
                title="상태 새로고침"
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
              </button>
          </div>

          {#if aiEnabled}
             <!-- Settings Section -->
             <div class="mb-4 border border-gray-200 rounded-lg overflow-hidden">
                <button 
                  on:click={() => showSettings = !showSettings}
                  class="w-full flex justify-between items-center px-4 py-2 bg-gray-50 text-sm font-medium text-gray-700 hover:bg-gray-100 transition-colors"
                >
                  <span>⚙️ 설정 (API Key)</span>
                  <span class="text-xs text-gray-500">{showSettings ? '▲' : '▼'}</span>
                </button>
                
                {#if showSettings}
                  <div transition:slide class="p-4 bg-white border-t border-gray-200">
                    <div class="flex gap-2">
                      <input 
                        type="password" 
                        bind:value={geminiKeyInput} 
                        placeholder="Gemini API Key 입력"
                        class="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
                      />
                      <button 
                        on:click={saveGeminiKey}
                        disabled={isGeminiLoading || !geminiKeyInput}
                        class="px-3 py-2 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                      >
                        저장
                      </button>
                    </div>
                    
                    {#if geminiStatus.enabled}
                      <div class="mt-2 flex justify-end">
                         <button 
                           on:click={deleteGeminiKey}
                           disabled={isGeminiLoading}
                           class="text-xs text-red-600 hover:text-red-800 underline decoration-red-300"
                         >
                           등록된 키 삭제하기
                         </button>
                      </div>
                    {/if}

                    <p class="text-[10px] text-gray-400 mt-2 flex items-center gap-1">
                      <span class="inline-block w-1 h-1 bg-gray-400 rounded-full"></span>
                      teacher_id는 현재 "Teacher"로 고정됩니다.
                    </p>
                  </div>
                {/if}
             </div>

             <!-- Test Prompt Section -->
             <div>
               <div class="relative">
                 <input  
                   type="text" 
                   bind:value={geminiTestPrompt} 
                   placeholder="AI에게 무엇이든 물어보세요..."
                   class="w-full px-4 py-3 pr-12 border border-gray-300 rounded-lg text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-purple-500 transition-all"
                   on:keydown={(e) => e.key === 'Enter' && testGemini()}
                 />
                 <button 
                   on:click={testGemini}
                   disabled={isGeminiLoading || !geminiTestPrompt}
                   class="absolute right-2 top-2 bottom-2 px-3 bg-purple-100 text-purple-700 rounded-md text-sm font-medium hover:bg-purple-200 disabled:opacity-50 transition-colors"
                 >
                   🚀
                 </button>
               </div>
               
               {#if isGeminiLoading}
                 <div class="mt-3 text-xs text-purple-600 flex items-center gap-2 animate-pulse">
                   <div class="w-2 h-2 bg-purple-600 rounded-full"></div>
                   Gemini가 답변을 생성중입니다...
                 </div>
               {/if}

               {#if geminiNotice}
                 <div class="mt-3 p-3 bg-green-50 border border-green-100 text-green-700 text-xs rounded-lg flex items-center gap-2" transition:slide>
                    <span>ℹ️</span> {geminiNotice}
                 </div>
               {/if}
               
               {#if geminiError}
                 <div class="mt-3 p-3 bg-red-50 border border-red-100 text-red-600 text-xs rounded-lg break-words flex items-center gap-2" transition:slide>
                   <span>⚠️</span> {geminiError}
                 </div>
               {/if}
               
               {#if geminiTestResponse}
                 <div class="mt-3 p-4 bg-purple-50 border border-purple-100 rounded-lg text-sm text-gray-800 whitespace-pre-wrap max-h-60 overflow-y-auto shadow-inner text-xs leading-relaxed" transition:slide>
                   {geminiTestResponse}
                 </div>
               {/if}
             </div>
          {:else}
             <div class="text-center py-6 bg-gray-50 rounded-lg border border-gray-100 border-dashed">
                <p class="text-gray-400 text-sm">AI 기능을 사용하려면 상단 스위치를 켜주세요.</p>
             </div>
          {/if}
        </div>

        <!-- Chat Panel -->
        <div class="bg-white rounded-lg shadow p-4 flex-1 flex flex-col min-h-[400px]">
          <h2 class="text-lg font-semibold mb-4 text-gray-800">💬 실시간 채팅</h2>
          
          <!-- Messages -->
          <div class="flex-1 overflow-y-auto space-y-3 mb-4">
            {#each messages as msg}
              <div class="p-3 rounded-lg {msg.sender === 'teacher' ? 'bg-blue-100 ml-auto' : 'bg-gray-100'} max-w-[80%]">
                <div class="text-xs text-gray-600 mb-1">{msg.sender === 'teacher' ? '나' : msg.sender}</div>
                <p class="text-sm text-gray-800">{msg.text}</p>
              </div>
            {/each}
          </div>

          <!-- Input -->
          <form on:submit|preventDefault={sendMessage} class="flex gap-2">
            <input
              type="text"
              bind:value={newMessage}
              placeholder="메시지 입력..."
              class="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button
              type="submit"
              class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
            >
              전송
            </button>
          </form>
        </div>
      </div>
    </div>
  </main>
</div>
