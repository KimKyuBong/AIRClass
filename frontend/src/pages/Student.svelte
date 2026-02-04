<script>
  import { onMount, onDestroy, tick } from 'svelte';
  
  let ws = null;
  let videoElement = null;
  let pc = null; // WebRTC PeerConnection
  let isConnected = false;
  let isVideoLoaded = false;
  let messages = [];
  let newMessage = '';
  let studentName = '';
  let isJoined = false;
  let streamToken = '';
  let webrtcUrl = '';
  let latencyMonitorInterval = null;
  let currentLatency = 0;
  let nodeInfo = null; // 연결된 노드 정보
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

  async function joinClass() {
    if (!studentName.trim()) return;
    
    localStorage.setItem('studentName', studentName);
    
    console.log('[Student] Joining class as:', studentName);
    
    // 1. 토큰 발급 받기
    try {
      const response = await fetch(`/api/token?user_type=student&user_id=${encodeURIComponent(studentName)}`, {
        method: 'POST'
      });
      const data = await response.json();
      streamToken = data.token;
      // 상대 경로인 경우 현재 origin 추가
      if (data.webrtc_url) {
        webrtcUrl = data.webrtc_url.startsWith('/') 
          ? window.location.origin + data.webrtc_url 
          : data.webrtc_url;
      } else {
        throw new Error('No webrtc_url in response');
      }
      
      // 노드 정보 저장
      nodeInfo = {
        mode: data.mode || 'unknown',
        node_name: data.node_name || 'unknown',
        node_id: data.node_id || 'unknown',
        host: data.host || window.location.hostname,
        webrtc_port: data.webrtc_url ? data.webrtc_url.split(':')[2]?.split('/')[0] : 'unknown'
      };
      
      console.log('[Student] Token received:', data);
      console.log('[Student] WebRTC URL:', webrtcUrl);
      console.log('[Student] Connected to node:', nodeInfo);
      
      // 2. Set joined state first to render the video element
      isJoined = true;
      
      // 3. Wait for DOM to update
      await tick();
      console.log('[Student] DOM updated, videoElement:', videoElement);
      
      // 4. Configure video element for ultra-low latency
      if (videoElement) {
        configureVideoForLowLatency(videoElement);
      }
      
      // 5. WebSocket 연결
      connectWebSocket();
      
      // 6. WebRTC 초기화 (토큰 포함)
      console.log('[Student] Initializing WebRTC...');
      initializeWebRTC(webrtcUrl);
      
    } catch (error) {
      alert('토큰 발급 실패: ' + error.message);
      console.error('Token error:', error);
    }
  }

  /**
   * 브라우저 SDP를 MediaMTX 호환 형식으로 변환
   * MediaMTX는 일부 브라우저 확장 속성을 지원하지 않으므로 제거
   * curl로 성공한 minimal SDP 형식에 맞춤
   */
  function cleanSdpForMediaMTX(sdp) {
    const lines = sdp.split('\r\n');
    const cleaned = [];
    let hasIceLite = false;
    let hasSetup = false;
    let bundleGroup = null;
    
    for (let line of lines) {
      // 빈 줄은 유지
      if (line.trim() === '') {
        cleaned.push(line);
        continue;
      }
      
      // 필수 속성은 모두 유지: v=, o=, s=, t=, m=, c=, a=mid, a=recvonly, a=rtcp-mux
      // a=rtpmap, a=fmtp, a=ice-ufrag, a=ice-pwd, a=fingerprint
      
      // 제거할 확장 속성들
      const removePatterns = [
        /^a=extmap-allow-mixed/,     // 확장 맵 혼합 허용
        /^a=msid-semantic:/,         // MSID 시맨틱
        /^a=extmap:/,                // 확장 맵 (일부는 유지해야 할 수도 있음)
      ];
      
      let shouldRemove = false;
      for (let pattern of removePatterns) {
        if (pattern.test(line)) {
          shouldRemove = true;
          break;
        }
      }
      
      // BUNDLE 그룹은 첫 번째만 유지
      if (line.startsWith('a=group:BUNDLE')) {
        if (!bundleGroup) {
          bundleGroup = line;
          cleaned.push(line);
        }
        shouldRemove = true;
      }
      
      // ice-lite 확인 (서버가 ice-lite를 사용하는 경우)
      if (line.startsWith('a=ice-lite')) {
        hasIceLite = true;
      }
      
      // setup 확인
      if (line.startsWith('a=setup:')) {
        hasSetup = true;
        // setup:active로 강제 설정 (클라이언트는 active여야 함)
        if (!line.includes('active')) {
          line = 'a=setup:active';
        }
      }
      
      if (!shouldRemove) {
        cleaned.push(line);
      }
    }
    
    // setup이 없으면 추가 (클라이언트는 active여야 함)
    if (!hasSetup) {
      // 마지막 m= 라인 뒤에 추가
      for (let i = cleaned.length - 1; i >= 0; i--) {
        if (cleaned[i].startsWith('m=')) {
          cleaned.splice(i + 1, 0, 'a=setup:active');
          break;
        }
      }
    }
    
    // SDP를 다시 조합
    let result = cleaned.join('\r\n');
    
    // 마지막에 빈 줄이 없으면 추가 (표준 SDP 형식)
    if (!result.endsWith('\r\n')) {
      result += '\r\n';
    }
    
    return result;
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

  async function initializeWebRTC(whepUrl, retryCount = 0) {
    console.log('[Student] initializeWebRTC called with URL:', whepUrl, 'retry:', retryCount);
    
    if (!videoElement) {
      console.error('[Student] videoElement not found! Retry count:', retryCount);
      
      // Retry up to 10 times with 200ms delay
      if (retryCount < 10) {
        setTimeout(() => initializeWebRTC(whepUrl, retryCount + 1), 200);
        return;
      } else {
        console.error('[Student] Failed to get videoElement after 10 retries');
        return;
      }
    }

    console.log('[Student] videoElement exists:', videoElement);
    console.log('[Student] Initializing WebRTC PeerConnection...');

    try {
      // Create RTCPeerConnection with ultra-low latency settings
      pc = new RTCPeerConnection({
        iceServers: [
          { urls: 'stun:stun.l.google.com:19302' }
        ],
        // Optimize for lowest latency
        bundlePolicy: 'max-bundle',
        rtcpMuxPolicy: 'require',
        iceCandidatePoolSize: 0  // Don't pre-gather candidates
      });

      // Handle incoming tracks (video/audio from server)
      pc.ontrack = (event) => {
        console.log('[Student] 🎥 Received track:', {
          kind: event.track.kind,
          id: event.track.id,
          readyState: event.track.readyState,
          muted: event.track.muted,
          enabled: event.track.enabled,
          streams: event.streams.length
        });
        
        event.track.onended = () => {
          console.log('[Student] ❌ Track ended:', event.track.kind);
        };
        
        event.track.onmute = () => {
          console.log('[Student] 🔇 Track muted:', event.track.kind);
        };
        
        event.track.onunmute = () => {
          console.log('[Student] 🔊 Track unmuted:', event.track.kind);
          // Try to play when track unmutes
          if (videoElement && videoElement.srcObject) {
            console.log('[Student] 🎬 Attempting playback after unmute...');
            videoElement.play().catch(err => console.warn('[Student] Playback attempt:', err.message));
          }
        };
        
        // Only set srcObject if we have a stream
        if (event.streams && event.streams.length > 0) {
          if (!videoElement.srcObject) {
            videoElement.srcObject = event.streams[0];
            console.log('[Student] ✅ Set video srcObject to stream, stream active:', event.streams[0].active);
            
            // Show video immediately when we get the first track
            isVideoLoaded = true;
            
            // Try to play immediately with aggressive retry
            setTimeout(() => {
              console.log('[Student] 🎬 Attempting immediate playback...');
              videoElement.play()
                .then(() => {
                  console.log('[Student] ▶️ Video playback started successfully');
                })
                .catch(err => {
                  console.warn('[Student] ⚠️ Playback failed:', err.message);
                  // Retry after a short delay
                  setTimeout(() => {
                    videoElement.play().catch(e => console.warn('[Student] Retry failed:', e.message));
                  }, 100);
                });
            }, 50); // Immediate attempt after 50ms
          }
          
          // Log stream tracks
          event.streams[0].getTracks().forEach(track => {
            console.log('[Student] Stream track:', {
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
        console.log('[Student] ICE connection state:', pc.iceConnectionState);
        
        if (pc.iceConnectionState === 'connected' || pc.iceConnectionState === 'completed') {
          console.log('[Student] 🎉 ICE connection established!');
          // Try to play when connection is established
          if (videoElement && videoElement.srcObject) {
            videoElement.play().catch(err => console.warn('[Student] Playback after ICE:', err.message));
          }
        }
        
        if (pc.iceConnectionState === 'failed' || pc.iceConnectionState === 'disconnected') {
          console.log('[Student] Connection failed, retrying in 3 seconds...');
          setTimeout(() => initializeWebRTC(whepUrl), 3000);
        }
      };

      // Handle ICE gathering state
      pc.onicegatheringstatechange = () => {
        console.log('[Student] ICE gathering state:', pc.iceGatheringState);
      };

      // Handle ICE candidates
      pc.onicecandidate = (event) => {
        if (event.candidate) {
          console.log('[Student] ICE candidate:', event.candidate.candidate);
        } else {
          console.log('[Student] ICE gathering complete');
        }
      };

      // Handle connection state
      pc.onconnectionstatechange = () => {
        console.log('[Student] Connection state:', pc.connectionState);
      };

      // Add transceiver to receive video with ultra-low latency settings
      const videoTransceiver = pc.addTransceiver('video', { 
        direction: 'recvonly'
      });
      const audioTransceiver = pc.addTransceiver('audio', { 
        direction: 'recvonly'
      });
      console.log('[Student] 📡 Added transceivers - video:', videoTransceiver.mid, 'audio:', audioTransceiver.mid);

      // Create offer
      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);

      console.log('[Student] Created offer, SDP length:', offer.sdp.length);
      console.log('[Student] SDP preview:', offer.sdp.substring(0, 500));
      
      // SDP를 MediaMTX 호환 형식으로 변환
      const cleanedSdp = cleanSdpForMediaMTX(offer.sdp);
      console.log('[Student] Cleaned SDP length:', cleanedSdp.length);
      console.log('[Student] Cleaned SDP preview:', cleanedSdp.substring(0, 500));

      console.log('[Student] Sending cleaned offer to WHEP endpoint:', whepUrl);

      // Send offer to WHEP endpoint with JWT token
      const response = await fetch(whepUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/sdp',
          'Authorization': `Bearer ${streamToken}`
        },
        body: cleanedSdp
      });

      if (!response.ok) {
        throw new Error(`WHEP request failed: ${response.status} ${response.statusText}`);
      }

      // Get answer from server
      const answerSdp = await response.text();
      console.log('[Student] 📥 Received answer from server, length:', answerSdp.length);
      console.log('[Student] Answer SDP preview:', answerSdp.substring(0, 200));
      // 디버깅: 서버 ICE 후보(포트) 확인
      const candLines = answerSdp.split('\r\n').filter(l => l.startsWith('a=candidate:') || l.startsWith('c='));
      if (candLines.length) console.log('[Student] Server ICE (c= / a=candidate):', candLines.slice(0, 10));

      await pc.setRemoteDescription({
        type: 'answer',
        sdp: answerSdp
      });

      console.log('[Student] ✅ WebRTC signaling complete! Waiting for ICE connection...');
      
      // Log current transceivers after remote description is set
      pc.getTransceivers().forEach((transceiver, index) => {
        console.log(`[Student] Transceiver ${index}:`, {
          mid: transceiver.mid,
          direction: transceiver.direction,
          currentDirection: transceiver.currentDirection,
          receiver: {
            track: transceiver.receiver.track ? {
              kind: transceiver.receiver.track.kind,
              id: transceiver.receiver.track.id,
              readyState: transceiver.receiver.track.readyState
            } : null
          }
        });
      });

    } catch (error) {
      console.error('[Student] WebRTC error:', error);
      if (retryCount < 5) {
        console.log('[Student] Retrying WebRTC connection in 3 seconds...');
        setTimeout(() => initializeWebRTC(whepUrl, retryCount + 1), 3000);
      } else {
        alert('WebRTC 연결 실패: ' + error.message);
      }
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
    if (pc) pc.close();
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
            <h2 class="text-lg font-semibold mb-4 text-gray-800">👨‍🏫 선생님 화면 (WebRTC 초저지연)</h2>
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
                    <p class="text-sm mt-2">WebRTC 연결 중</p>
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
