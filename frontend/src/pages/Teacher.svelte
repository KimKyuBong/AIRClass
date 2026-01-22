<script>
  import { onMount, onDestroy } from 'svelte';
  import Hls from 'hls.js';
  
  let ws = null;
  let videoElement = null;
  let hls = null;
  let isConnected = false;
  let isVideoLoaded = false;
  let students = [];
  let messages = [];
  let newMessage = '';
  let hlsUrl = null;

  onMount(async () => {
    connectWebSocket();
    await fetchTokenAndInitHLS();
  });

  onDestroy(() => {
    if (hls) {
      hls.destroy();
    }
    if (ws) {
      ws.close();
    }
  });

  async function fetchTokenAndInitHLS() {
    try {
      // Get JWT token from backend
      const response = await fetch(
        `http://${window.location.hostname}:8000/api/token?user_type=teacher&user_id=Teacher`,
        { method: 'POST' }
      );
      
      if (!response.ok) {
        throw new Error('Failed to get token');
      }
      
      const data = await response.json();
      hlsUrl = data.hls_url; // URL includes JWT token
      
      // Initialize HLS with token-authenticated URL
      initializeHLS(hlsUrl);
    } catch (error) {
      console.error('Error fetching token:', error);
      // Retry after 3 seconds
      setTimeout(fetchTokenAndInitHLS, 3000);
    }
  }

  function initializeHLS(url) {
    if (!videoElement) {
      setTimeout(() => initializeHLS(url), 100);
      return;
    }

    if (Hls.isSupported()) {
      hls = new Hls({
        enableWorker: true,
        lowLatencyMode: true,
        backBufferLength: 90
      });
      
      hls.loadSource(url);
      hls.attachMedia(videoElement);
      
      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        console.log('HLS manifest loaded');
        videoElement.play().catch(e => console.log('Autoplay prevented:', e));
        isVideoLoaded = true;
      });

      hls.on(Hls.Events.ERROR, (event, data) => {
        console.error('HLS error:', data);
        if (data.fatal) {
          switch (data.type) {
            case Hls.ErrorTypes.NETWORK_ERROR:
              console.log('Network error, trying to recover...');
              hls.startLoad();
              break;
            case Hls.ErrorTypes.MEDIA_ERROR:
              console.log('Media error, trying to recover...');
              hls.recoverMediaError();
              break;
            default:
              console.log('Fatal error, destroying HLS...');
              hls.destroy();
              setTimeout(() => fetchTokenAndInitHLS(), 3000);
              break;
          }
        }
      });
    } else if (videoElement.canPlayType('application/vnd.apple.mpegurl')) {
      // Safari native HLS support
      videoElement.src = url;
      videoElement.addEventListener('loadedmetadata', () => {
        videoElement.play().catch(e => console.log('Autoplay prevented:', e));
        isVideoLoaded = true;
      });
    }
  }

  function connectWebSocket() {
    ws = new WebSocket(`ws://${window.location.hostname}:8000/ws/teacher`);
    
    ws.onopen = () => {
      isConnected = true;
      console.log('Teacher WebSocket connected');
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.type === 'student_list') {
        // 학생 목록 업데이트
        students = data.students.map(name => ({
          name: name,
          joinedAt: new Date().toLocaleTimeString('ko-KR')
        }));
      } else if (data.type === 'chat') {
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
</script>

<div class="min-h-screen bg-gray-50">
  <!-- Header -->
  <header class="bg-white border-b border-gray-200 px-6 py-4 shadow-sm">
    <div class="flex items-center justify-between max-w-7xl mx-auto">
      <div class="flex items-center gap-3">
        <div class="w-3 h-3 rounded-full {isConnected ? 'bg-green-500' : 'bg-red-500'}"></div>
        <h1 class="text-2xl font-bold text-gray-800">👨‍🏫 AIRClass Teacher</h1>
      </div>
      <div class="flex items-center gap-4">
        <div class="text-sm text-gray-600">
          학생 {students.length}명 접속 중
        </div>
        <div class="text-xs text-gray-500">
          HLS Stream
        </div>
      </div>
    </div>
  </header>

  <main class="max-w-7xl mx-auto p-6">
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Screen Preview -->
      <div class="lg:col-span-2">
        <div class="bg-white rounded-lg shadow p-4">
          <h2 class="text-lg font-semibold mb-4 text-gray-800">내 화면 미리보기</h2>
          <div class="bg-gray-900 rounded-lg aspect-video flex items-center justify-center overflow-hidden">
            {#if isVideoLoaded}
              <!-- svelte-ignore a11y-media-has-caption -->
              <video
                bind:this={videoElement}
                class="w-full h-full object-contain"
                autoplay
                muted
                playsinline
              ></video>
            {:else}
              <div class="text-center text-gray-400">
                <div class="text-4xl mb-2">📱</div>
                <p>Android 앱에서 화면 공유 시작</p>
                <p class="text-xs mt-2">HLS: {hlsUrl || 'Loading...'}</p>
              </div>
            {/if}
          </div>
        </div>

        <!-- Student List -->
        <div class="bg-white rounded-lg shadow p-4 mt-6">
          <h2 class="text-lg font-semibold mb-4 text-gray-800">접속 중인 학생</h2>
          <div class="space-y-2">
            {#each students as student}
              <div class="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                <div class="w-2 h-2 bg-green-500 rounded-full"></div>
                <span class="text-sm text-gray-700">{student.name}</span>
                <span class="text-xs text-gray-500 ml-auto">{student.joinedAt}</span>
              </div>
            {:else}
              <p class="text-sm text-gray-500 text-center py-4">접속 중인 학생이 없습니다</p>
            {/each}
          </div>
        </div>
      </div>

      <!-- Chat Panel -->
      <div class="lg:col-span-1">
        <div class="bg-white rounded-lg shadow p-4 h-[calc(100vh-200px)] flex flex-col">
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
