<script>
  import { onMount, onDestroy, tick } from 'svelte';
  
  let ws = null;
  let videoElement = null;
  let pc = null; // WebRTC PeerConnection
  let isConnected = false;
  let isVideoLoaded = false;
  let students = [];
  let messages = [];
  let newMessage = '';
  let webrtcUrl = '';
  let latencyMonitorInterval = null;
  let currentLatency = 0;
  
  // WebRTC viewer tracking
  let viewers = [];
  let viewerCount = 0;
  let viewerPollInterval = null;
  let streamReady = false;
  let nodeStats = {};
  let clusterMode = 'unknown';

  onMount(async () => {
    console.log('[Teacher] Component mounted');
    connectWebSocket();
    await fetchTokenAndInitWebRTC();
    startViewerPolling();
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
    if (viewerPollInterval) {
      clearInterval(viewerPollInterval);
    }
  });

  async function fetchTokenAndInitWebRTC() {
    try {
      console.log('[Teacher] Fetching token...');
      const response = await fetch(
        `http://${window.location.hostname}:8000/api/token?user_type=teacher&user_id=Teacher`,
        { method: 'POST' }
      );
      
      if (!response.ok) {
        throw new Error('Failed to get token');
      }
      
      const data = await response.json();
      webrtcUrl = data.webrtc_url;
      
      console.log('[Teacher] Token received:', data);
      console.log('[Teacher] WebRTC URL:', webrtcUrl);
      
      // Wait for DOM to update
      await tick();
      console.log('[Teacher] DOM updated, videoElement:', videoElement);
      
      // Configure video element for ultra-low latency
      if (videoElement) {
        configureVideoForLowLatency(videoElement);
      }
      
      // Initialize WebRTC
      console.log('[Teacher] Initializing WebRTC...');
      initializeWebRTC(webrtcUrl);
      
    } catch (error) {
      console.error('[Teacher] Token error:', error);
      // Retry after 3 seconds
      setTimeout(fetchTokenAndInitWebRTC, 3000);
    }
  }

  // Configure video element for ultra-low latency
  function configureVideoForLowLatency(video) {
    console.log('[Teacher] Configuring video for ultra-low latency');
    
    // Disable buffering for Firefox
    if (video.mozPreservesPitch !== undefined) {
      video.mozPreservesPitch = false;
    }
    
    // Force immediate playback without buffering
    video.addEventListener('loadedmetadata', () => {
      console.log('[Teacher] Video metadata loaded, forcing immediate playback');
      video.play().catch(err => console.warn('[Teacher] Immediate play failed:', err.message));
    });
    
    // Monitor video lag and keep at live edge
    latencyMonitorInterval = setInterval(() => {
      if (video.buffered.length > 0) {
        const currentTime = video.currentTime;
        const bufferedEnd = video.buffered.end(video.buffered.length - 1);
        const lag = bufferedEnd - currentTime;
        currentLatency = Math.round(lag * 1000); // Convert to ms
        
        // If lag exceeds 200ms, jump to live edge
        if (lag > 0.2) {
          console.warn('[Teacher] ⚠️ Video lag detected:', lag.toFixed(3), 's - jumping to live edge');
          video.currentTime = bufferedEnd - 0.02;
        }
        
        // If lag exceeds 500ms, something is wrong
        if (lag > 0.5) {
          console.error('[Teacher] 🔴 CRITICAL LAG:', lag.toFixed(3), 's - forcing live edge');
          video.currentTime = bufferedEnd - 0.01;
        }
      }
    }, 50);
  }

  async function initializeWebRTC(whepUrl, retryCount = 0) {
    console.log('[Teacher] initializeWebRTC called with URL:', whepUrl, 'retry:', retryCount);
    
    if (!videoElement) {
      console.error('[Teacher] videoElement not found! Retry count:', retryCount);
      
      if (retryCount < 10) {
        setTimeout(() => initializeWebRTC(whepUrl, retryCount + 1), 200);
        return;
      } else {
        console.error('[Teacher] Failed to get videoElement after 10 retries');
        return;
      }
    }

    console.log('[Teacher] videoElement exists:', videoElement);
    console.log('[Teacher] Initializing WebRTC PeerConnection...');

    try {
      // Create RTCPeerConnection with ultra-low latency settings
      pc = new RTCPeerConnection({
        iceServers: [
          { urls: 'stun:stun.l.google.com:19302' }
        ],
        bundlePolicy: 'max-bundle',
        rtcpMuxPolicy: 'require',
        iceCandidatePoolSize: 0
      });

      // Handle incoming tracks
      pc.ontrack = (event) => {
        console.log('[Teacher] 🎥 Received track:', {
          kind: event.track.kind,
          id: event.track.id,
          readyState: event.track.readyState,
          muted: event.track.muted,
          enabled: event.track.enabled,
          streams: event.streams.length
        });
        
        event.track.onended = () => {
          console.log('[Teacher] ❌ Track ended:', event.track.kind);
        };
        
        event.track.onmute = () => {
          console.log('[Teacher] 🔇 Track muted:', event.track.kind);
        };
        
        event.track.onunmute = () => {
          console.log('[Teacher] 🔊 Track unmuted:', event.track.kind);
          if (videoElement && videoElement.srcObject) {
            console.log('[Teacher] 🎬 Attempting playback after unmute...');
            videoElement.play().catch(err => console.warn('[Teacher] Playback attempt:', err.message));
          }
        };
        
        if (event.streams && event.streams.length > 0) {
          if (!videoElement.srcObject) {
            videoElement.srcObject = event.streams[0];
            console.log('[Teacher] ✅ Set video srcObject to stream');
            
            isVideoLoaded = true;
            
            setTimeout(() => {
              console.log('[Teacher] 🎬 Attempting immediate playback...');
              videoElement.play()
                .then(() => {
                  console.log('[Teacher] ▶️ Video playback started successfully');
                })
                .catch(err => {
                  console.warn('[Teacher] ⚠️ Playback failed:', err.message);
                  setTimeout(() => {
                    videoElement.play().catch(e => console.warn('[Teacher] Retry failed:', e.message));
                  }, 100);
                });
            }, 50);
          }
          
          event.streams[0].getTracks().forEach(track => {
            console.log('[Teacher] Stream track:', {
              kind: track.kind,
              id: track.id,
              readyState: track.readyState,
              enabled: track.enabled,
              muted: track.muted
            });
          });
        }
      };

      // Handle ICE connection state changes
      pc.oniceconnectionstatechange = () => {
        console.log('[Teacher] ICE connection state:', pc.iceConnectionState);
        
        if (pc.iceConnectionState === 'connected' || pc.iceConnectionState === 'completed') {
          console.log('[Teacher] 🎉 ICE connection established!');
          if (videoElement && videoElement.srcObject) {
            videoElement.play().catch(err => console.warn('[Teacher] Playback after ICE:', err.message));
          }
        }
        
        if (pc.iceConnectionState === 'failed' || pc.iceConnectionState === 'disconnected') {
          console.log('[Teacher] Connection failed, retrying in 3 seconds...');
          setTimeout(() => initializeWebRTC(whepUrl), 3000);
        }
      };

      pc.onicegatheringstatechange = () => {
        console.log('[Teacher] ICE gathering state:', pc.iceGatheringState);
      };

      pc.onicecandidate = (event) => {
        if (event.candidate) {
          console.log('[Teacher] ICE candidate:', event.candidate.candidate);
        } else {
          console.log('[Teacher] ICE gathering complete');
        }
      };

      pc.onconnectionstatechange = () => {
        console.log('[Teacher] Connection state:', pc.connectionState);
      };

      // Add transceiver to receive video
      const videoTransceiver = pc.addTransceiver('video', { 
        direction: 'recvonly'
      });
      const audioTransceiver = pc.addTransceiver('audio', { 
        direction: 'recvonly'
      });
      console.log('[Teacher] 📡 Added transceivers - video:', videoTransceiver.mid, 'audio:', audioTransceiver.mid);

      // Create offer
      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);

      console.log('[Teacher] Created offer, sending to WHEP endpoint:', whepUrl);

      // Send offer to WHEP endpoint
      const response = await fetch(whepUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/sdp'
        },
        body: offer.sdp
      });

      if (!response.ok) {
        throw new Error(`WHEP request failed: ${response.status} ${response.statusText}`);
      }

      // Get answer from server
      const answerSdp = await response.text();
      console.log('[Teacher] 📥 Received answer from server, length:', answerSdp.length);

      await pc.setRemoteDescription({
        type: 'answer',
        sdp: answerSdp
      });

      console.log('[Teacher] ✅ WebRTC signaling complete! Waiting for ICE connection...');
      
      pc.getTransceivers().forEach((transceiver, index) => {
        console.log(`[Teacher] Transceiver ${index}:`, {
          mid: transceiver.mid,
          direction: transceiver.direction,
          currentDirection: transceiver.currentDirection
        });
      });

    } catch (error) {
      console.error('[Teacher] WebRTC error:', error);
      if (retryCount < 5) {
        console.log('[Teacher] Retrying WebRTC connection in 3 seconds...');
        setTimeout(() => initializeWebRTC(whepUrl, retryCount + 1), 3000);
      }
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
    // Initial fetch
    fetchViewers();
    
    // Poll every 2 seconds
    viewerPollInterval = setInterval(async () => {
      await fetchViewers();
    }, 2000);
  }
  
  async function fetchViewers() {
    try {
      const response = await fetch(`http://${window.location.hostname}:8000/api/viewers`);
      if (response.ok) {
        const data = await response.json();
        viewerCount = data.total_viewers || 0;
        viewers = data.viewers || [];
        streamReady = data.stream_ready || false;
        nodeStats = data.node_stats || {};
        clusterMode = data.cluster_mode || 'unknown';
        console.log('[Teacher] Viewers updated:', viewerCount, 'viewers', Object.keys(nodeStats).length, 'nodes');
      } else {
        console.error('[Teacher] Failed to fetch viewers:', response.status);
      }
    } catch (error) {
      console.error('[Teacher] Error fetching viewers:', error);
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
        {#if currentLatency > 0}
          <span class="text-xs px-2 py-1 rounded {currentLatency < 300 ? 'bg-green-100 text-green-800' : currentLatency < 1000 ? 'bg-yellow-100 text-yellow-800' : 'bg-red-100 text-red-800'}">
            {currentLatency}ms
          </span>
        {/if}
      </div>
      <div class="flex items-center gap-4">
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
          <h2 class="text-lg font-semibold mb-4 text-gray-800">내 화면 미리보기 (WebRTC 초저지연)</h2>
          <div class="bg-gray-900 rounded-lg aspect-video flex items-center justify-center overflow-hidden relative">
            <!-- svelte-ignore a11y-media-has-caption -->
            <video
              bind:this={videoElement}
              class="w-full h-full object-contain"
              autoplay
              muted
              playsinline
              disablepictureinpicture
              style="object-fit: contain;"
            ></video>
            
            {#if !isVideoLoaded}
              <div class="absolute inset-0 flex items-center justify-center text-center text-gray-400 bg-gray-900 bg-opacity-90">
                <div>
                  <div class="text-4xl mb-2">📱</div>
                  <p>Android 앱에서 화면 공유 시작</p>
                  <p class="text-sm mt-2">WebRTC 연결 중...</p>
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
