<script>
  import { onMount, onDestroy } from 'svelte';
  import Hls from 'hls.js';
  
  let ws = null;
  let videoElement = null;
  let hls = null;
  let isConnected = false;
  let isVideoLoaded = false;
  let error = null;
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
        `http://${window.location.hostname}:8000/api/token?user_type=monitor&user_id=Monitor`,
        { method: 'POST' }
      );
      
      if (!response.ok) {
        throw new Error('Failed to get token');
      }
      
      const data = await response.json();
      hlsUrl = data.hls_url; // URL includes JWT token
      
      // Initialize HLS with token-authenticated URL
      initializeHLS(hlsUrl);
    } catch (err) {
      console.error('Error fetching token:', err);
      error = 'Failed to get authentication token';
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
        error = null;
      });

      hls.on(Hls.Events.ERROR, (event, data) => {
        console.error('HLS error:', data);
        if (data.fatal) {
          switch (data.type) {
            case Hls.ErrorTypes.NETWORK_ERROR:
              console.log('Network error, trying to recover...');
              error = 'Network error - retrying...';
              hls.startLoad();
              break;
            case Hls.ErrorTypes.MEDIA_ERROR:
              console.log('Media error, trying to recover...');
              error = 'Media error - recovering...';
              hls.recoverMediaError();
              break;
            default:
              console.log('Fatal error, destroying HLS...');
              error = 'Fatal error - reconnecting...';
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
        error = null;
      });
    }
  }

  function connectWebSocket() {
    try {
      ws = new WebSocket(`ws://${window.location.hostname}:8000/ws/monitor`);
      
      ws.onopen = () => {
        isConnected = true;
        console.log('Monitor WebSocket connected for keepalive');
      };

      ws.onerror = (err) => {
        console.error('WebSocket error:', err);
      };

      ws.onclose = () => {
        isConnected = false;
        setTimeout(connectWebSocket, 3000);
      };
    } catch (err) {
      console.error('WebSocket connection error:', err);
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
    {#if isVideoLoaded}
      <div class="max-w-7xl w-full h-full flex items-center justify-center">
        <!-- svelte-ignore a11y-media-has-caption -->
        <video
          bind:this={videoElement}
          class="w-full h-full object-contain rounded-lg shadow-2xl"
          autoplay
          muted
          playsinline
        ></video>
      </div>
    {:else}
      <div class="text-center">
        {#if error}
          <div class="text-yellow-500 text-xl mb-4">⚠️ {error}</div>
        {:else}
          <div class="text-6xl mb-4">📱</div>
          <p class="text-xl text-gray-400">화면을 기다리는 중...</p>
        {/if}
        <p class="text-sm text-gray-500 mt-2">Android 앱에서 화면 공유를 시작하세요</p>
        <p class="text-xs text-gray-600 mt-2">{hlsUrl || 'Loading...'}</p>
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
