<script>
  import { onMount, onDestroy } from 'svelte';
  import Hls from 'hls.js';
  
  let ws = null;
  let videoElement = null;
  let hls = null;
  let isConnected = false;
  let isVideoLoaded = false;
  let messages = [];
  let newMessage = '';
  let studentName = '';
  let isJoined = false;
  let streamToken = '';

  onMount(() => {
    studentName = localStorage.getItem('studentName') || '';
  });

  onDestroy(() => {
    if (hls) {
      hls.destroy();
    }
    if (ws) {
      ws.close();
    }
  });

  async function joinClass() {
    if (!studentName.trim()) return;
    
    localStorage.setItem('studentName', studentName);
    
    // 1. 토큰 발급 받기
    try {
      const response = await fetch(`http://${window.location.hostname}:8000/api/token?user_type=student&user_id=${encodeURIComponent(studentName)}`, {
        method: 'POST'
      });
      const data = await response.json();
      streamToken = data.token;
      
      // 2. WebSocket 연결
      connectWebSocket();
      
      // 3. HLS 초기화 (토큰 포함)
      initializeHLS(data.hls_url);
      
      isJoined = true;
    } catch (error) {
      alert('토큰 발급 실패: ' + error.message);
      console.error('Token error:', error);
    }
  }

  function initializeHLS(hlsUrl) {
    if (!videoElement) return;

    if (Hls.isSupported()) {
      hls = new Hls({
        enableWorker: true,
        lowLatencyMode: true,
        backBufferLength: 90
      });
      
      hls.loadSource(hlsUrl);
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
              setTimeout(initializeHLS, 3000);
              break;
          }
        }
      });
    } else if (videoElement.canPlayType('application/vnd.apple.mpegurl')) {
      // Safari native HLS support
      videoElement.src = hlsUrl;
      videoElement.addEventListener('loadedmetadata', () => {
        videoElement.play().catch(e => console.log('Autoplay prevented:', e));
        isVideoLoaded = true;
      });
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
    if (hls) hls.destroy();
    isJoined = false;
    isConnected = false;
    isVideoLoaded = false;
  }
</script>

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
            <h2 class="text-lg font-semibold mb-4 text-gray-800">👨‍🏫 선생님 화면</h2>
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
                  <div class="text-4xl mb-2">⏳</div>
                  <p>선생님 화면을 기다리는 중...</p>
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
