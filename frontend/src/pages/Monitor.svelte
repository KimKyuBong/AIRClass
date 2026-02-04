<script>
  import { onMount, onDestroy, tick } from 'svelte';
  
  let ws = null;
  let videoElement = null;
  let pc = null; // WebRTC PeerConnection
  let isConnected = false;
  let isVideoLoaded = false;
  let error = null;
  let webrtcUrl = '';
  let streamToken = '';
  let latencyMonitorInterval = null;
  let currentLatency = 0;

  onMount(async () => {
    console.log('[Monitor] Component mounted');
    connectWebSocket();
    await fetchTokenAndInitWebRTC();
  });

  onDestroy(() => {
    if (pc) {
      pc.close();
    }
    if (ws) {
      ws.close();
    }
    if (latencyMonitorInterval) {
      clearInterval(latencyMonitorInterval);
    }
  });

  async function fetchTokenAndInitWebRTC() {
    try {
      console.log('[Monitor] Fetching token...');
      const response = await fetch(
        `http://${window.location.hostname}:8000/api/token?user_type=monitor&user_id=Monitor`,
        { method: 'POST' }
      );
      
      if (!response.ok) {
        throw new Error('Failed to get token');
      }
      
      const data = await response.json();
      webrtcUrl = data.webrtc_url;
      streamToken = data.token;
      
      console.log('[Monitor] Token received:', data);
      console.log('[Monitor] WebRTC URL:', webrtcUrl);
      
      // Wait for DOM to update
      await tick();
      
      // Configure video element
      if (videoElement) {
        configureVideoForLowLatency(videoElement);
      }
      
      // Initialize WebRTC
      console.log('[Monitor] Initializing WebRTC...');
      initializeWebRTC(webrtcUrl);
      
    } catch (err) {
      console.error('[Monitor] Error fetching token:', err);
      error = 'Failed to get authentication token';
      setTimeout(fetchTokenAndInitWebRTC, 3000);
    }
  }

  /**
   * 브라우저 SDP를 MediaMTX 호환 형식으로 변환
   */
  function cleanSdpForMediaMTX(sdp) {
    const lines = sdp.split('\r\n');
    const cleaned = [];
    let hasSetup = false;
    let bundleGroup = null;
    
    for (let line of lines) {
      if (line.trim() === '') {
        cleaned.push(line);
        continue;
      }
      
      const removePatterns = [
        /^a=extmap-allow-mixed/,
        /^a=msid-semantic:/,
        /^a=extmap:/,
      ];
      
      let shouldRemove = false;
      for (let pattern of removePatterns) {
        if (pattern.test(line)) {
          shouldRemove = true;
          break;
        }
      }
      
      if (line.startsWith('a=group:BUNDLE')) {
        if (!bundleGroup) {
          bundleGroup = line;
          cleaned.push(line);
        }
        shouldRemove = true;
      }
      
      if (line.startsWith('a=setup:')) {
        hasSetup = true;
        if (!line.includes('active')) {
          line = 'a=setup:active';
        }
      }
      
      if (!shouldRemove) {
        cleaned.push(line);
      }
    }
    
    if (!hasSetup) {
      for (let i = cleaned.length - 1; i >= 0; i--) {
        if (cleaned[i].startsWith('m=')) {
          cleaned.splice(i + 1, 0, 'a=setup:active');
          break;
        }
      }
    }
    
    let result = cleaned.join('\r\n');
    if (!result.endsWith('\r\n')) {
      result += '\r\n';
    }
    
    return result;
  }

  function configureVideoForLowLatency(video) {
    console.log('[Monitor] Configuring video for ultra-low latency');
    
    if (video.mozPreservesPitch !== undefined) {
      video.mozPreservesPitch = false;
    }
    
    video.addEventListener('loadedmetadata', () => {
      console.log('[Monitor] Video metadata loaded');
      video.play().catch(err => console.warn('[Monitor] Play failed:', err.message));
    });
    
    latencyMonitorInterval = setInterval(() => {
      if (video.buffered.length > 0) {
        const currentTime = video.currentTime;
        const bufferedEnd = video.buffered.end(video.buffered.length - 1);
        const lag = bufferedEnd - currentTime;
        currentLatency = Math.round(lag * 1000);
        
        if (lag > 0.2) {
          video.currentTime = bufferedEnd - 0.02;
        }
      }
    }, 50);
  }

  async function initializeWebRTC(whepUrl, retryCount = 0) {
    console.log('[Monitor] initializeWebRTC called with URL:', whepUrl);
    
    if (!videoElement) {
      if (retryCount < 10) {
        setTimeout(() => initializeWebRTC(whepUrl, retryCount + 1), 200);
        return;
      } else {
        error = 'Failed to initialize video element';
        return;
      }
    }

    try {
      pc = new RTCPeerConnection({
        iceServers: [
          { urls: 'stun:stun.l.google.com:19302' }
        ],
        bundlePolicy: 'max-bundle',
        rtcpMuxPolicy: 'require',
        iceCandidatePoolSize: 0
      });

      pc.ontrack = (event) => {
        console.log('[Monitor] 🎥 Received track:', event.track.kind);
        
        if (event.streams && event.streams.length > 0) {
          if (!videoElement.srcObject) {
            videoElement.srcObject = event.streams[0];
            console.log('[Monitor] ✅ Set video srcObject');
            
            isVideoLoaded = true;
            error = null;
            
            setTimeout(() => {
              videoElement.play()
                .then(() => console.log('[Monitor] ▶️ Playback started'))
                .catch(err => console.warn('[Monitor] Playback failed:', err.message));
            }, 50);
          }
        }
      };

      pc.oniceconnectionstatechange = () => {
        console.log('[Monitor] ICE state:', pc.iceConnectionState);
        
        if (pc.iceConnectionState === 'connected' || pc.iceConnectionState === 'completed') {
          console.log('[Monitor] 🎉 Connected!');
          if (videoElement && videoElement.srcObject) {
            videoElement.play().catch(err => console.warn('[Monitor] Play error:', err.message));
          }
        }
        
        if (pc.iceConnectionState === 'failed' || pc.iceConnectionState === 'disconnected') {
          error = 'Connection lost - retrying...';
          setTimeout(() => initializeWebRTC(whepUrl), 3000);
        }
      };

      pc.onconnectionstatechange = () => {
        console.log('[Monitor] Connection state:', pc.connectionState);
      };

      const videoTransceiver = pc.addTransceiver('video', { direction: 'recvonly' });
      const audioTransceiver = pc.addTransceiver('audio', { direction: 'recvonly' });

      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);

      // SDP를 MediaMTX 호환 형식으로 변환
      const cleanedSdp = cleanSdpForMediaMTX(offer.sdp);
      console.log('[Monitor] Cleaned SDP length:', cleanedSdp.length);

      const response = await fetch(whepUrl, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/sdp',
          'Authorization': `Bearer ${streamToken}`
        },
        body: cleanedSdp
      });

      if (!response.ok) {
        throw new Error(`WHEP failed: ${response.status}`);
      }

      const answerSdp = await response.text();
      await pc.setRemoteDescription({ type: 'answer', sdp: answerSdp });

      console.log('[Monitor] ✅ WebRTC signaling complete');

    } catch (err) {
      console.error('[Monitor] WebRTC error:', err);
      error = 'WebRTC connection error';
      if (retryCount < 5) {
        setTimeout(() => initializeWebRTC(whepUrl, retryCount + 1), 3000);
      }
    }
  }

  function connectWebSocket() {
    try {
      ws = new WebSocket(`ws://${window.location.hostname}:8000/ws/monitor`);
      
      ws.onopen = () => {
        isConnected = true;
        console.log('[Monitor] WebSocket connected');
      };

      ws.onerror = (err) => {
        console.error('[Monitor] WebSocket error:', err);
      };

      ws.onclose = () => {
        isConnected = false;
        setTimeout(connectWebSocket, 3000);
      };
    } catch (err) {
      console.error('[Monitor] WebSocket connection error:', err);
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
        {#if currentLatency > 0}
          <span class="text-xs px-2 py-1 rounded bg-green-900 text-green-300">
            {currentLatency}ms
          </span>
        {/if}
      </div>
      <div class="text-sm text-gray-400">
        {isConnected ? '연결됨' : '연결 중...'} · WebRTC 초저지연
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
          disablepictureinpicture
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
        <p class="text-xs text-gray-600 mt-2">WebRTC 연결 중...</p>
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
