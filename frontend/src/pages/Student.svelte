<script>
  import { onMount, onDestroy, tick } from 'svelte';
  import { Room, RoomEvent } from 'livekit-client';
  import 'vidstack/player';
  import 'vidstack/player/ui';
  import 'vidstack/player/layouts/default';
  import 'vidstack/icons';
  
  let ws = null;
  let broadcastStream = null;
  let livekitRoom = null;
  let isConnected = false;
  let isVideoLoaded = false;
  let messages = [];
  let newMessage = '';
  let studentName = '';
  let isJoined = false;
  let nodeInfo = { mode: 'LiveKit', node_name: 'LiveKit', node_id: 'class' };
  let isPortraitVideo = false; // 세로 모드 영상 여부
  let videoContainerClass = ''; // 동적 컨테이너 클래스
  let videoContainer = null;
  let videoElement = null;
  let mediaPlayerEl = null;
  let videoAspectRatio = '16/9';
  let showVideoControls = false;
  let isFullscreen = false;
  let isPip = false;
  let isJoining = false;

  // Reactive: isPortraitVideo 변경 시 videoContainerClass 자동 업데이트
  $: videoContainerClass = isPortraitVideo ? 'portrait-video' : 'landscape-video';

  function onFullscreenChange() {
    isFullscreen = !!document.fullscreenElement;
  }
  function onPipChange() {
    isPip = !!document.pictureInPictureElement;
  }

  onMount(async () => {
    console.log('[Student] Component mounted');
    document.addEventListener('fullscreenchange', onFullscreenChange);
    document.addEventListener('pictureinpicturechange', onPipChange);

    // URL 쿼리 파라미터에서 name 가져오기
    const urlParams = new URLSearchParams(window.location.search);
    const nameFromUrl = urlParams.get('name');
    
    console.log('[Student] Name from URL:', nameFromUrl);
    
    if (nameFromUrl) {
      // URL에 name이 있으면 자동으로 참여
      studentName = nameFromUrl;
      console.log('[Student] Auto-joining with name:', studentName);
      await joinClass();
    }
  });

  onDestroy(() => {
    document.removeEventListener('fullscreenchange', onFullscreenChange);
    document.removeEventListener('pictureinpicturechange', onPipChange);
    if (livekitRoom) {
      livekitRoom.disconnect();
    }
    if (ws) {
      ws.close();
    }
  });

  async function joinClass() {
    if (!studentName.trim()) return;
    if (isJoining) return;
    isJoining = true;

    try {
      console.log('[Student] Joining class...');
      // Detect if running in Android emulator
      const isEmulator = window.location.hostname === '10.0.2.2' || 
                        /Android.*Emulator|wv/.test(navigator.userAgent);
      const emulatorParam = isEmulator ? '&emulator=true' : '';
      const response = await fetch(`/api/livekit/token?user_id=${encodeURIComponent(studentName)}&room_name=class&user_type=student${emulatorParam}`, { method: 'POST' });
      if (!response.ok) throw new Error('Failed to get token');
      
      const { token, url } = await response.json();

      if (livekitRoom) {
        await livekitRoom.disconnect();
        livekitRoom = null;
        await new Promise((r) => setTimeout(r, 150));
      }

      livekitRoom = new Room({
        adaptiveStream: true,
        dynacast: true,
      });

      // Connection state monitoring
      livekitRoom.on(RoomEvent.ConnectionStateChanged, (state) => {
        console.log('[Student] LiveKit connection state:', state);
      });

      console.log('[Student] Connecting to LiveKit...', { url, token: token.substring(0, 10) + '...' });
      try {
        await livekitRoom.connect(url, token);
        console.log('[Student] Connected to LiveKit room');
        isJoined = true;
        connectWebSocket();
      } catch (e) {
        console.error('[Student] LiveKit connection failed:', e);
        error = `LiveKit 연결 실패: ${e.message}`;
        isLoading = false;
        return;
      }
      
      livekitRoom.on(RoomEvent.TrackSubscribed, async (track, publication, participant) => {
        console.log('[Student] Track subscribed:', track.kind, 'from', participant.identity);
        if (track.kind === 'video') {
          broadcastStream = new MediaStream([track.mediaStreamTrack]);
          isVideoLoaded = true;
          
          await tick();
          if (videoElement) {
            track.attach(videoElement);
            console.log('[Student] Track attached to video element');
          }
          
          // Detect aspect ratio
          const videoTrack = track.mediaStreamTrack;
          const settings = videoTrack.getSettings();
          if (settings.width && settings.height) {
            videoAspectRatio = `${settings.width}/${settings.height}`;
            isPortraitVideo = settings.height > settings.width;
          }
        }
      });

      livekitRoom.on(RoomEvent.TrackUnsubscribed, (track, publication, participant) => {
        if (track.kind === 'video') {
          track.detach(videoElement);
          if (broadcastStream) {
            broadcastStream = null;
            isVideoLoaded = false;
          }
        }
      });

      // Handle existing tracks
      console.log('[Student] Checking existing tracks, remoteParticipants:', livekitRoom.remoteParticipants.size);
      for (const participant of livekitRoom.remoteParticipants.values()) {
        console.log('[Student] Participant:', participant.identity, 'trackPublications:', participant.trackPublications?.size || 0);
        for (const publication of participant.trackPublications.values()) {
          console.log('[Student] Publication:', publication.trackName, 'isSubscribed:', publication.isSubscribed, 'hasTrack:', !!publication.track);
          
          if (publication.isSubscribed && publication.track) {
            const track = publication.track;
            broadcastStream = new MediaStream([track.mediaStreamTrack]);
            isVideoLoaded = true;
            
            await tick();
            if (videoElement) {
              track.attach(videoElement);
              console.log('[Student] Existing track attached to video element');
            }
            
            const settings = track.mediaStreamTrack.getSettings();
            if (settings.width && settings.height) {
              videoAspectRatio = `${settings.width}/${settings.height}`;
              isPortraitVideo = settings.height > settings.width;
            }
          } else if (!publication.isSubscribed) {
            console.log('[Student] Track not subscribed yet, subscribing:', publication.trackSid);
            await publication.subscribe();
          }
        }
      }
      
    } catch (error) {
      console.error('[Student] Join failed:', error);
      const msg = error?.message || String(error);
      const hint = msg.includes('Abort') || msg.includes('signal connection')
        ? '\n\n(같은 네트워크에서 서버 주소·7880 포트 접속이 가능한지 확인하세요.)'
        : '';
      alert('수업 참여에 실패했습니다.' + hint);
    } finally {
      isJoining = false;
    }
  }

  function connectWebSocket() {
    ws = new WebSocket(`ws://${window.location.hostname}:8000/ws/student?name=${encodeURIComponent(studentName)}`);
    
    ws.onopen = () => {
      isConnected = true;
      console.log('Student WebSocket connected');
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.type === 'chat') {
        // 채팅 메시지 처리
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

  function leaveClass() {
    if (ws) ws.close();
    if (livekitRoom) livekitRoom.disconnect();
    isJoined = false;
    isConnected = false;
    isVideoLoaded = false;
    if (document.fullscreenElement) document.exitFullscreen();
    if (document.pictureInPictureElement) document.exitPictureInPicture();
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
      } else {
        console.warn('PIP: no video or player found');
      }
    } catch (e) {
      console.warn('PIP error:', e);
    }
  }
</script>

<style>
  /* 기본 비디오 스타일 - 크롭 방지를 위해 contain 강제 */
  video, .video-stream {
    width: 100% !important;
    height: 100% !important;
    object-fit: contain !important;
    background-color: black !important;
  }

  /* 비디오 컨테이너: 송출(스트림) 비율에 맞춰 크기 결정 (가로 100%, 높이는 aspect-ratio로) */
  .portrait-video, .landscape-video {
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    background-color: black !important;
    width: 100% !important;
    height: auto !important;
    min-height: 200px;
  }

  .video-container {
    max-width: 100%;
  }

  .video-container-inner {
    width: 100% !important;
    height: 100% !important;
  }

  /* 전체화면: 화면 전체 채우고 비디오는 contain으로 전부 보이기 */
  .video-container:fullscreen {
    width: 100vw !important;
    height: 100vh !important;
    background: black !important;
    display: flex !important;
    justify-content: center !important;
    align-items: center !important;
    max-width: none !important;
    max-height: none !important;
    aspect-ratio: unset !important;
  }

  .video-container:fullscreen .video-container-inner {
    width: 100% !important;
    height: 100% !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    background: black !important;
  }

  .video-container:fullscreen .video-container-inner media-player {
    width: 100% !important;
    height: 100% !important;
    display: block !important;
  }

  /* shadow DOM 안의 video까지 적용 (vidstack) */
  .video-container:fullscreen .video-container-inner video,
  .video-container:fullscreen video,
  :global(.video-container:fullscreen) video {
    width: 100% !important;
    height: 100% !important;
    object-fit: contain !important;
  }

  ::backdrop {
    background-color: black !important;
  }
</style>

{#if !isJoined}
  <!-- Join Screen -->
  <div class="min-h-screen bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center p-6">
    <div class="bg-white rounded-2xl shadow-2xl p-8 max-w-md w-full">
      <div class="text-center mb-8">
        <div class="text-6xl mb-4">🎓</div>
        <h1 class="text-3xl font-bold text-gray-800 mb-2">AIRClass</h1>
        <p class="text-gray-600">수업에 참여하세요</p>
      </div>

      <form on:submit|preventDefault={joinClass} class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">
            이름
          </label>
          <input
            type="text"
            bind:value={studentName}
            placeholder="이름을 입력하세요"
            class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            required
          />
        </div>

        <button
          type="submit"
          class="w-full bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700 transition"
        >
          수업 참여하기
        </button>
      </form>
    </div>
  </div>
{:else}
  <!-- Class Screen -->
  <div class="min-h-screen bg-gray-50">
    <!-- Header -->
    <header class="bg-white border-b border-gray-200 px-6 py-4 shadow-sm">
      <div class="flex items-center justify-between max-w-7xl mx-auto">
        <div class="flex items-center gap-3">
          <div class="w-3 h-3 rounded-full {isConnected ? 'bg-green-500' : 'bg-red-500'}"></div>
          <h1 class="text-xl font-bold text-gray-800">🎓 {studentName}님의 수업</h1>
          {#if nodeInfo}
            {@const subNodeNum = nodeInfo.node_id?.match(/sub-(\d+)/)?.[1] || nodeInfo.node_name?.match(/sub-?(\d+)/i)?.[1] || null}
            <span class="text-xs px-2 py-1 rounded bg-blue-100 text-blue-800 font-mono" title="노드 ID: {nodeInfo.node_id}">
              {#if nodeInfo.mode === 'sub'}
                {#if subNodeNum}
                  서브 노드 #{subNodeNum} ({nodeInfo.node_id})
                {:else}
                  서브 노드: {nodeInfo.node_name} ({nodeInfo.node_id})
                {/if}
              {:else if nodeInfo.mode === 'main'}
                메인 노드: {nodeInfo.node_name}
              {:else if nodeInfo.mode === 'LiveKit'}
                {nodeInfo.node_name}
              {:else}
                {nodeInfo.node_name} ({nodeInfo.mode})
              {/if}
            </span>
          {/if}
        </div>
        <button
          on:click={leaveClass}
          class="px-4 py-2 text-sm text-red-600 hover:bg-red-50 rounded-lg transition"
        >
          나가기
        </button>
      </div>
    </header>

    <main class="max-w-7xl mx-auto p-6">
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <!-- Teacher's Screen -->
        <div class="lg:col-span-2">
          <div class="bg-white rounded-lg shadow p-4">
            <h2 class="text-lg font-semibold mb-4 text-gray-800">👨‍🏫 선생님 화면 (LiveKit 초저지연)</h2>
            <div 
              bind:this={videoContainer}
              class="bg-black rounded-lg overflow-hidden relative {videoContainerClass} video-container"
              style="aspect-ratio: {videoAspectRatio};"
              role="presentation"
            >
              <div class="video-container-inner w-full h-full min-w-0 min-h-0 flex items-center justify-center">
                <video
                  bind:this={videoElement}
                  autoplay
                  muted
                  playsinline
                  class="w-full h-full object-contain bg-black"
                  class:hidden={!broadcastStream}
                ></video>
              </div>

              <!-- PIP / 전체화면 버튼 -->
              {#if isVideoLoaded && broadcastStream}
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
              
              <!-- Loading overlay - shows on top when video not loaded -->
              {#if !isVideoLoaded}
                <div class="absolute inset-0 z-50 flex items-center justify-center text-center text-gray-400 bg-gray-900 bg-opacity-90">
                  <div>
                    <div class="text-4xl mb-2">⏳</div>
                    <p>선생님 화면을 기다리는 중...</p>
                    <p class="text-sm mt-2">LiveKit 연결 중</p>
                  </div>
                </div>
              {/if}
            </div>
          </div>
        </div>

        <!-- Chat Panel -->
        <div class="lg:col-span-1">
          <div class="bg-white rounded-lg shadow p-4 h-[calc(100vh-200px)] flex flex-col">
            <h2 class="text-lg font-semibold mb-4 text-gray-800">💬 질문하기</h2>
            
            <!-- Messages -->
            <div class="flex-1 overflow-y-auto space-y-3 mb-4">
              {#each messages as msg}
                <div class="p-3 rounded-lg {msg.sender === studentName ? 'bg-blue-100 ml-auto' : 'bg-gray-100'} max-w-[80%]">
                  <div class="text-xs text-gray-600 mb-1">
                    {msg.sender === 'teacher' ? '👨‍🏫 선생님' : msg.sender === studentName ? '나' : msg.sender}
                  </div>
                  <p class="text-sm text-gray-800">{msg.text}</p>
                </div>
              {/each}
            </div>

            <!-- Input -->
            <form on:submit|preventDefault={sendMessage} class="flex gap-2">
              <input
                type="text"
                bind:value={newMessage}
                placeholder="질문을 입력하세요..."
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
{/if}
