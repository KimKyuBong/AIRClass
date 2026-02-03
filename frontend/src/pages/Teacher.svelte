<script>
  import { onMount, onDestroy, tick } from 'svelte';
  import { slide } from 'svelte/transition';
  
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

  let isBroadcasting = false;
  let broadcastStream = null;
  
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

  onMount(async () => {
    console.log('[Teacher] Component mounted');
    
    // Gemini Status Check
    fetchGeminiStatus();
    
    // 전역 에러 핸들러 추가 (콘솔 못 보는 환경용)
    window.onerror = function(msg, url, line, col, error) {
      alert(`💥 GLOBAL ERROR 💥\n\nMsg: ${msg}\nLine: ${line}:${col}\nError: ${error ? error.stack : 'N/A'}`);
      return false;
    };

    connectWebSocket();
    // Default to viewer mode (Android stream)
    streamSource = 'android';
    await fetchTokenAndInitWebRTC();
    startViewerPolling();
  });

  // 버튼 클릭 핸들러 단순화
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

  async function startBroadcast() {
    try {
      if (isBroadcasting) return;

      // Check for secure context
      if (!navigator.mediaDevices || !navigator.mediaDevices.getDisplayMedia) {
        throw new Error(
          '브라우저가 화면 공유를 지원하지 않습니다.\n(원인: HTTPS가 아니거나 localhost가 아님)\n현재 주소: ' + window.location.href
        );
      }
      
      console.log('[Teacher] Starting broadcast...');
      
      // 1. Get Display Media first
      try {
        broadcastStream = await navigator.mediaDevices.getDisplayMedia({
          video: {
            width: { ideal: 1920 },
            height: { ideal: 1080 },
            frameRate: { ideal: 30 }
          },
          audio: true
        });
      } catch (e) {
        if (e.name === 'NotAllowedError') {
          // 사용자가 취소함 -> 조용히 리턴
          console.log('User cancelled screen share');
          return;
        }
        throw new Error(`화면 선택 실패: ${e.name} - ${e.message}`);
      }
      
      // Handle user cancelling the picker
      broadcastStream.getVideoTracks()[0].onended = () => {
        console.log('[Teacher] User stopped screen share via browser UI');
        stopBroadcast();
      };
      
      // 2. Get Publish Token
      console.log('[Teacher] Fetching publish token...');
      let response;
      try {
        response = await fetch(
          `/api/token?user_type=teacher&user_id=Teacher&action=publish`,
          { method: 'POST' }
        );
      } catch (e) {
        throw new Error(`토큰 요청 중 네트워크 오류 발생 (Mixed Content 또는 서버 다운?)\n${e.message}`);
      }
      
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`토큰 발급 실패 (Status: ${response.status})\n서버 응답: ${errorText}`);
      }
      
      const data = await response.json();
      let whipUrl = data.webrtc_url;
      
      // Proxy를 타도록 상대 경로로 변환
      let originalWhipUrl = whipUrl;
      try {
        const urlObj = new URL(whipUrl);
        whipUrl = urlObj.pathname + urlObj.search;
      } catch (e) {
        console.warn('URL parsing failed, using original', e);
      }
      
      // 3. Stop existing viewer PC if any
      if (pc) {
        pc.close();
        pc = null;
      }
      
      // 4. Create Publisher PeerConnection
      pc = new RTCPeerConnection({
        iceServers: [{ urls: 'stun:stun.l.google.com:19302' }],
        bundlePolicy: 'max-bundle',
        rtcpMuxPolicy: 'require'
      });
      
      // Add tracks
      broadcastStream.getTracks().forEach(track => {
        pc.addTrack(track, broadcastStream);
      });
      
      if (videoElement) {
        videoElement.srcObject = broadcastStream;
        videoElement.muted = true;
        videoElement.play().catch(e => console.error('Preview play failed', e));
      }

      // 5. Create Offer
      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);
      
      // 6. WHIP Signaling
      console.log(`[Teacher] Sending offer to WHIP endpoint: ${whipUrl}`);
      let whipResponse;
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000); // 10초 타임아웃

        whipResponse = await fetch(whipUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/sdp' },
          body: offer.sdp,
          signal: controller.signal
        });
        clearTimeout(timeoutId);
      } catch (e) {
         if (e.name === 'AbortError') {
            throw new Error(`방송 서버 연결 시간 초과 (10초).\n네트워크 상태를 확인하거나 서버 로그를 확인하세요.`);
         }
         throw new Error(`방송 서버(WHIP) 연결 실패.\n요청 URL: ${whipUrl}\n(원본: ${originalWhipUrl})\n에러: ${e.message}\n\n* HTTPS 접속 시 프록시 설정이 안되었거나 인증서 문제일 수 있습니다.`);
      }
      
      if (!whipResponse.ok) {
        const errText = await whipResponse.text();
        throw new Error(`방송 시작 실패 (MediaMTX 오류)\nStatus: ${whipResponse.status}\n응답: ${errText}`);
      }
      
      const answerSdp = await whipResponse.text();
      await pc.setRemoteDescription({ type: 'answer', sdp: answerSdp });
      
      isBroadcasting = true;
      isVideoLoaded = true;
      
    } catch (error) {
      console.error('[Teacher] Broadcast failed:', error);
      stopBroadcast();
      
      // 사용자 요청대로 원본 에러 메시지와 스택 트레이스를 그대로 출력
      const errorDump = [
        `Message: ${error.message}`,
        `Name: ${error.name}`,
        `Stack: ${error.stack || 'N/A'}`,
        // fetch 에러인 경우 추가 정보가 있을 수 있음
        error.cause ? `Cause: ${JSON.stringify(error.cause)}` : ''
      ].filter(Boolean).join('\n\n');

      alert(`🚨 CRITICAL ERROR 🚨\n\n${errorDump}`);
    }
  }

  function stopBroadcast() {
    if (!isBroadcasting && !broadcastStream) return;
    
    console.log('[Teacher] Stopping broadcast...');
    
    // Stop tracks
    if (broadcastStream) {
      broadcastStream.getTracks().forEach(track => track.stop());
      broadcastStream = null;
    }
    
    // Close PC
    if (pc) {
      pc.close();
      pc = null;
    }
    
    if (videoElement) {
      videoElement.srcObject = null;
    }
    
    isBroadcasting = false;
    isVideoLoaded = false;
    
    // Revert to Android viewer mode
    console.log('[Teacher] Reverting to Android viewer mode...');
    streamSource = 'android';
    fetchTokenAndInitWebRTC();
  }

  // 스트림 소스 전환 함수
  async function switchStreamSource(newSource) {
    if (isSourceSwitching) return;
    if (streamSource === newSource && !isBroadcasting) return;
    
    isSourceSwitching = true;
    console.log(`[Teacher] Switching stream source from ${streamSource} to ${newSource}`);
    
    try {
      // 기존 연결 정리
      if (isBroadcasting) {
        stopBroadcast();
      } else if (pc) {
        pc.close();
        pc = null;
      }
      
      if (videoElement) {
        videoElement.srcObject = null;
      }
      
      isVideoLoaded = false;
      streamSource = newSource;
      
      // 새 소스로 연결
      if (newSource === 'android') {
        // Android 스트림 시청 모드
        console.log('[Teacher] Switching to Android stream viewer mode');
        await fetchTokenAndInitWebRTC();
      } else if (newSource === 'pc') {
        // PC 화면 공유 시작
        console.log('[Teacher] Switching to PC broadcast mode');
        await startBroadcast();
      }
    } catch (error) {
      console.error('[Teacher] Error switching stream source:', error);
      alert(`소스 전환 실패: ${error.message}`);
      // 실패 시 Android로 복귀
      streamSource = 'android';
      await fetchTokenAndInitWebRTC();
    } finally {
      isSourceSwitching = false;
    }
  }

  async function fetchTokenAndInitWebRTC() {
    if (isBroadcasting) return; // Don't interrupt broadcast

    try {
      console.log('[Teacher] Fetching viewer token...');
      // Use relative path for proxy support (HTTPS)
      const response = await fetch(
        `/api/token?user_type=teacher&user_id=Teacher&action=read`,
        { method: 'POST' }
      );
      
      if (!response.ok) {
        throw new Error('Failed to get token');
      }
      
      const data = await response.json();
      webrtcUrl = data.webrtc_url;
      
      // Proxy를 타도록 상대 경로로 변환 (HTTPS -> HTTP Mixed Content 방지)
      try {
        const urlObj = new URL(webrtcUrl);
        webrtcUrl = urlObj.pathname + urlObj.search;
        console.log('[Teacher] Converted WHEP URL to relative:', webrtcUrl);
      } catch (e) {
        console.warn('[Teacher] Failed to convert WHEP URL:', e);
      }
      
      console.log('[Teacher] Token received:', data);
      
      // Wait for DOM to update
      await tick();
      
      // Initialize WebRTC as viewer
      initializeWebRTC(webrtcUrl);
      
    } catch (error) {
      console.error('[Teacher] Token error:', error);
      // Retry logic handled by caller or refresh
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
      
      if (line.startsWith('a=ice-lite')) {
        hasIceLite = true;
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

      console.log('[Teacher] Created offer, SDP length:', offer.sdp.length);
      
      // SDP를 MediaMTX 호환 형식으로 변환
      const cleanedSdp = cleanSdpForMediaMTX(offer.sdp);
      console.log('[Teacher] Cleaned SDP length:', cleanedSdp.length);

      console.log('[Teacher] Sending cleaned offer to WHEP endpoint:', whepUrl);

      // Send offer to WHEP endpoint
      const response = await fetch(whepUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/sdp'
        },
        body: cleanedSdp
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
    // Initial fetch
    fetchViewers();
    
    // Poll every 2 seconds
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
        console.log('[Teacher] Viewers updated:', viewerCount, 'viewers', Object.keys(nodeStats).length, 'nodes');
      } else {
        console.error('[Teacher] Failed to fetch viewers:', response.status);
      }
    } catch (error) {
      console.error('[Teacher] Error fetching viewers:', error);
    }
  }

  // Gemini API Functions
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
      }
    } catch (e) {
      console.error('Failed to fetch Gemini status', e);
    }
  }

  async function saveGeminiKey() {
    if (!geminiKeyInput.trim()) return;
    isGeminiLoading = true;
    geminiError = '';
    geminiNotice = '';
    try {
      // Note: In production, send via body. Using query params as requested.
      const res = await fetch(`/api/ai/keys/gemini?teacher_id=Teacher&api_key=${encodeURIComponent(geminiKeyInput)}`, {
        method: 'POST'
      });
      if (!res.ok) throw new Error(await res.text());
      geminiKeyInput = ''; // Clear input
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
