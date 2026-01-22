<script>
  import { onMount } from 'svelte';
  
  let ws = null;
  let currentImage = null;
  let isConnected = false;
  let error = null;

  onMount(() => {
    connectWebSocket();
    return () => {
      if (ws) ws.close();
    };
  });

  function connectWebSocket() {
    try {
      ws = new WebSocket(`ws://${window.location.hostname}:8000/ws/monitor`);
      
      ws.onopen = () => {
        isConnected = true;
        error = null;
        console.log('Monitor WebSocket connected');
      };

      ws.onmessage = (event) => {
        currentImage = event.data;
      };

      ws.onerror = (err) => {
        error = 'WebSocket connection error';
        console.error('WebSocket error:', err);
      };

      ws.onclose = () => {
        isConnected = false;
        // 재연결 시도
        setTimeout(connectWebSocket, 3000);
      };
    } catch (err) {
      error = err.message;
    }
  }
</script>

<div class="min-h-screen bg-gray-900 text-white">
  <!-- Header -->
  <header class="bg-gray-800 border-b border-gray-700 px-6 py-4">
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-3">
        <div class="w-3 h-3 rounded-full {isConnected ? 'bg-green-500' : 'bg-red-500'} animate-pulse"></div>
        <h1 class="text-2xl font-bold">AIRClass Monitor</h1>
      </div>
      <div class="text-sm text-gray-400">
        {isConnected ? '연결됨' : '연결 중...'}
      </div>
    </div>
  </header>

  <!-- Main Screen -->
  <main class="flex items-center justify-center p-6" style="height: calc(100vh - 80px);">
    {#if error}
      <div class="text-center">
        <div class="text-red-500 text-xl mb-4">⚠️ 연결 오류</div>
        <p class="text-gray-400">{error}</p>
      </div>
    {:else if currentImage}
      <div class="max-w-7xl w-full">
        <img 
          src={currentImage} 
          alt="Screen capture"
          class="w-full h-auto rounded-lg shadow-2xl"
        />
      </div>
    {:else}
      <div class="text-center">
        <div class="text-6xl mb-4">📱</div>
        <p class="text-xl text-gray-400">화면을 기다리는 중...</p>
        <p class="text-sm text-gray-500 mt-2">Android 앱에서 화면 공유를 시작하세요</p>
      </div>
    {/if}
  </main>
</div>

<style>
  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
  }
  .animate-pulse {
    animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
  }
</style>
