<script>
  import { onMount, onDestroy, tick } from 'svelte';
  import { Room, RoomEvent } from 'livekit-client';
  
  let ws = null;
  let videoElement = null;
  let livekitRoom = null;
  let isConnected = false;
  let isVideoLoaded = false;
  let messages = [];
  let newMessage = '';
  let studentName = '';
  let isJoined = false;
  let latencyMonitorInterval = null;
  let currentLatency = 0;
  let nodeInfo = { mode: 'LiveKit', node_name: 'LiveKit', node_id: 'class' };
  let isPortraitVideo = false; // 세로 모드 영상 여부
  let videoContainerClass = ''; // 동적 컨테이너 클래스
  
  // Reactive: isPortraitVideo 변경 시 videoContainerClass 자동 업데이트
  $: videoContainerClass = isPortraitVideo ? 'portrait-video' : 'landscape-video';

  onMount(async () => {
    console.log('[Student] Component mounted');
    
    // URL 쿼리 파라미터에서 name 가져오기
    const urlParams = new URLSearchParams(window.location.search);
    const nameFromUrl = urlParams.get('name');
    
    console.log('[Student] Name from URL:', nameFromUrl);
    
    if (nameFromUrl) {
      // URL에 name이 있으면 자동으로 참여
      studentName = nameFromUrl;
      console.log('[Student] Auto-joining with name:', studentName);
      await joinClass();
    } else {
      // URL에 name이 없으면 localStorage에서 가져오기
      studentName = localStorage.getItem('studentName') || '';
      console.log('[Student] Name from localStorage:', studentName);
    }
  });

  onDestroy(() => {
    if (livekitRoom) {
      livekitRoom.disconnect();
    }
    if (ws) {
      ws.close();
    }
    if (latencyMonitorInterval) {
      clearInterval(latencyMonitorInterval);
    }
  });

  async function joinClass() {
    if (!studentName.trim()) return;
    
    try {
      // 1. Save name
      localStorage.setItem('studentName', studentName);
      console.log('[Student] Joining class as:', studentName);
      
      // 2. Get LiveKit token
      console.log('[Student] Fetching token from:', `/api/livekit/token?user_id=${encodeURIComponent(studentName)}&room_name=class&user_type=student`);
      const response = await fetch(`/api/livekit/token?user_id=${encodeURIComponent(studentName)}&room_name=class&user_type=student`, { 
        method: 'POST' 
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Token API failed (${response.status}): ${errorText}`);
      }
      
      const { token, url } = await response.json();
      
      console.log('[Student] LiveKit token received');
      console.log('[Student] LiveKit URL:', url);
      
      // 3. Set joined state (triggers DOM update)
      isJoined = true;
      await tick();
      
      // 4. Connect to LiveKit room
      console.log('[Student] Creating LiveKit Room...');
      livekitRoom = new Room();
      console.log('[Student] Connecting to:', url);
      await livekitRoom.connect(url, token);
      console.log('[Student] ✅ Connected to LiveKit room');
      
      // 5. Subscribe to remote tracks
      livekitRoom.on(RoomEvent.TrackSubscribed, (track, publication, participant) => {
        console.log('[Student] Track subscribed:', track.kind, 'from', participant.identity);
        if (track.kind === 'video') {
          console.log('[Student] Attaching video track to element');
          const element = track.attach();
          element.id = 'remote-video';
          videoElement.replaceWith(element);
          videoElement = element;
          isVideoLoaded = true;
          configureVideoForLowLatency(videoElement);
        }
      });
      
      // Handle tracks from participants already in the room
      console.log('[Student] Checking for existing participants...');
      livekitRoom.remoteParticipants.forEach(participant => {
        console.log('[Student] Found existing participant:', participant.identity);
        participant.trackPublications.forEach(publication => {
          if (publication.isSubscribed && publication.track?.kind === 'video') {
            console.log('[Student] Attaching existing video track');
            const element = publication.track.attach();
            element.id = 'remote-video';
            videoElement.replaceWith(element);
            videoElement = element;
            isVideoLoaded = true;
            configureVideoForLowLatency(videoElement);
          }
        });
      });
      
      // 6. Connect WebSocket for chat
      connectWebSocket();
      
    } catch (error) {
      console.error('[Student] Join failed:', error);
      console.error('[Student] Error stack:', error.stack);
      alert(`수업 참여 실패:\n\n${error.message}\n\n브라우저 콘솔(F12)에서 자세한 에러를 확인하세요.`);
    }
  }

  // Configure video element for ultra-low latency
  function configureVideoForLowLatency(video) {
    console.log('[Student] Configuring video for ultra-low latency');
    
    // Disable buffering for Firefox
    if (video.mozPreservesPitch !== undefined) {
      video.mozPreservesPitch = false;
    }
    
    // Force immediate playback without buffering
    video.addEventListener('loadedmetadata', () => {
      console.log('[Student] Video metadata loaded, forcing immediate playback');
      
      // 비디오 크기 감지 및 aspect ratio 계산
      const videoWidth = video.videoWidth;
      const videoHeight = video.videoHeight;
      const aspectRatio = videoWidth / videoHeight;
      
      console.log('[Student] Video dimensions:', videoWidth, 'x', videoHeight, 'aspect ratio:', aspectRatio.toFixed(2));
      
      // 세로 모드 판단 (높이가 너비보다 큰 경우)
      isPortraitVideo = videoHeight > videoWidth;
      
      if (isPortraitVideo) {
        console.log('[Student] 📱 Portrait mode detected - using cover for full screen');
        videoContainerClass = 'portrait-video';
      } else {
        console.log('[Student] 🖥️ Landscape mode detected - using contain');
        videoContainerClass = 'landscape-video';
      }
      
      video.play().catch(err => console.warn('[Student] Immediate play failed:', err.message));
    });
    
    // Monitor video lag and keep at live edge - AGGRESSIVE MODE
    latencyMonitorInterval = setInterval(() => {
      if (video.buffered.length > 0) {
        const currentTime = video.currentTime;
        const bufferedEnd = video.buffered.end(video.buffered.length - 1);
        const lag = bufferedEnd - currentTime;
        currentLatency = Math.round(lag * 1000); // Convert to ms
        
        // AGGRESSIVE: If lag exceeds 200ms, jump to live edge
        if (lag > 0.2) {
          console.warn('[Student] ⚠️ Video lag detected:', lag.toFixed(3), 's - jumping to live edge');
          video.currentTime = bufferedEnd - 0.02; // Stay 20ms behind live edge
        }
        
        // ULTRA-AGGRESSIVE: If lag exceeds 500ms, something is wrong
        if (lag > 0.5) {
          console.error('[Student] 🔴 CRITICAL LAG:', lag.toFixed(3), 's - forcing live edge');
          video.currentTime = bufferedEnd - 0.01; // Force to 10ms behind
        }
      }
    }, 50); // Check every 50ms (increased from 100ms) for faster response
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
    if (latencyMonitorInterval) clearInterval(latencyMonitorInterval);
    isJoined = false;
    isConnected = false;
    isVideoLoaded = false;
  }
</script>

<style>
  /* 기본 비디오 스타일 */
  .video-stream {
    width: 100%;
    height: 100%;
    object-fit: contain;
  }

  /* 가로 모드 비디오 (기본) */
  .landscape-video .video-stream {
    object-fit: contain; /* 전체를 보여주며 비율 유지 */
  }

  /* 세로 모드 비디오 - 화면에 꽉 차게 */
  .portrait-video {
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .portrait-video .video-stream {
    width: auto !important;
    height: 100% !important;
    max-width: 100%;
    object-fit: cover; /* 화면을 꽉 채움 */
  }

  /* 반응형: 작은 화면에서는 세로 영상이 너비에 맞춰지도록 */
  @media (max-width: 768px) {
    .portrait-video .video-stream {
      width: 100% !important;
      height: auto !important;
      max-height: 100%;
    }
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
          {#if currentLatency > 0}
            <span class="text-xs px-2 py-1 rounded {currentLatency < 300 ? 'bg-green-100 text-green-800' : currentLatency < 1000 ? 'bg-yellow-100 text-yellow-800' : 'bg-red-100 text-red-800'}">
              {currentLatency}ms
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
            <div class="bg-gray-900 rounded-lg aspect-video flex items-center justify-center overflow-hidden relative {videoContainerClass}">
              <!-- Video element with ultra-low latency settings - ALWAYS visible -->
              <!-- svelte-ignore a11y-media-has-caption -->
              <video
                bind:this={videoElement}
                class="video-stream"
                autoplay
                muted
                playsinline
                disablepictureinpicture
              ></video>
              
              <!-- Loading overlay - shows on top when video not loaded -->
              {#if !isVideoLoaded}
                <div class="absolute inset-0 flex items-center justify-center text-center text-gray-400 bg-gray-900 bg-opacity-90">
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
