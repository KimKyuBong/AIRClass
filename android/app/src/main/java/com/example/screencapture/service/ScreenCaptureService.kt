package com.example.screencapture.service

import android.animation.ObjectAnimator
import android.animation.ValueAnimator
import android.view.animation.AccelerateDecelerateInterpolator
import android.graphics.PointF
import kotlin.math.cos
import kotlin.math.sin

class ScreenCaptureService : Service(), ConnectChecker {

    companion object {
        private const val TAG = "ScreenCaptureService"
        // ... (기존 상수 유지)
        
        // 상태 코드 (기존 유지)
        const val STATUS_STARTING = "starting"
        const val STATUS_CONNECTING = "connecting"
        const val STATUS_CONNECTED = "connected"
        const val STATUS_FAILED = "failed"
        const val STATUS_DISCONNECTED = "disconnected"
    }

    // ... (기존 변수 유지)

    // Floating Control & Menu
    private var floatingLayout: FrameLayout? = null 
    private var mainBall: ImageView? = null 
    private var menuContainer: FrameLayout? = null 
    private var isMenuExpanded = false
    private var breathingAnimator: ObjectAnimator? = null
    
    // Status Colors
    private val COLOR_NORMAL = Color.parseColor("#4CAF50") // Green (Connected)
    private val COLOR_WARNING = Color.parseColor("#FFC107") // Amber (Connecting)
    private val COLOR_ERROR = Color.parseColor("#F44336") // Red (Error)
    private var currentStatusColor = COLOR_WARNING // Default to connecting

    // ... (기존 코드 유지)

    // Keep-Alive Logic: 부드러운 호흡 애니메이션
    // 투명도를 0.6 ~ 0.65 사이에서 1초간 부드럽게 왕복시켜 화면을 강제로 갱신함
    private fun startKeepAliveAnimation() {
        stopKeepAliveAnimation()
        
        // floatingLayout이 생성된 후에 실행해야 함
        if (floatingLayout == null) {
            // 뷰가 아직 없으면 잠시 후 재시도
            android.os.Handler(android.os.Looper.getMainLooper()).postDelayed({
                if (isStreaming) startKeepAliveAnimation()
            }, 1000)
            return
        }

        Log.i(TAG, "✨ Starting breathing animation (Alpha 0.60 <-> 0.65) for static screen support")
        
        breathingAnimator = ObjectAnimator.ofFloat(floatingLayout, "alpha", 0.60f, 0.65f).apply {
            duration = 1000 // 1초
            repeatMode = ValueAnimator.REVERSE
            repeatCount = ValueAnimator.INFINITE
            interpolator = AccelerateDecelerateInterpolator() // 부드러운 가감속
            
            // 값이 변할 때마다 레이아웃 갱신을 확실하게 보장
            addUpdateListener { 
                if (floatingLayout != null && floatingLayoutParams != null) {
                    try {
                        windowManager?.updateViewLayout(floatingLayout, floatingLayoutParams)
                    } catch (e: Exception) {
                        // ignore
                    }
                }
            }
            start()
        }
    }

    private fun stopKeepAliveAnimation() {
        breathingAnimator?.cancel()
        breathingAnimator = null
        floatingLayout?.alpha = 0.6f // 기본값 복귀
        Log.i(TAG, "✨ Breathing animation stopped")
    }

    // ... (기존 생명주기 메서드 등 유지)

    // ConnectChecker 콜백에서 상태 색상 업데이트 호출
    override fun onConnectionStarted(url: String) {
        Log.d(TAG, "🔄 Connection starting to: $url")
        updateNotification("연결 중...")
        sendStatusBroadcast(STATUS_CONNECTING, "서버에 연결 중...", url)
        updateStatusColor(STATUS_CONNECTING)
    }

    override fun onConnectionSuccess() {
        Log.d(TAG, "✅ Connection success")
        retryCount = 0 
        reconnectHandler.removeCallbacks(reconnectRunnable)
        
        updateNotification("연결 성공 - 스트리밍 중")
        sendStatusBroadcast(STATUS_CONNECTED, "연결 성공! 스트리밍 중")
        updateStatusColor(STATUS_CONNECTED)
        
        startHeartbeat()
    }

    override fun onConnectionFailed(reason: String) {
        Log.e(TAG, "❌ Connection failed: $reason")
        updateStatusColor(STATUS_FAILED)
        
        if (isIntentionalStop) return

        retryCount++
        val delay = calculateRetryDelay(retryCount)
        
        updateNotification("연결 실패. ${delay/1000}초 후 재시도 (${retryCount}회)")
        sendStatusBroadcast(STATUS_CONNECTING, "서버 연결 실패. ${delay/1000}초 후 재시도 중... (${retryCount}회)")
        
        reconnectHandler.postDelayed(reconnectRunnable, delay)
    }

    override fun onDisconnect() {
        Log.d(TAG, "🔌 Disconnected from server")
        updateStatusColor(STATUS_DISCONNECTED)
        
        if (isIntentionalStop) {
            updateNotification("연결 끊김")
            sendStatusBroadcast(STATUS_DISCONNECTED, "서버와 연결이 끊어졌습니다")
            return
        }
        
        // Unexpected disconnect logic...
        retryCount++
        val delay = 3000L
        updateNotification("서버 재연결 대기 중...")
        sendStatusBroadcast(STATUS_CONNECTING, "재연결 대기 중...")
        
        // Try internal retry
        try {
            rtmpDisplay.getStreamClient().reTry(delay, "Unexpected disconnect", rtmpUrl)
        } catch (e: Exception) {
            stopHeartbeat()
        }
    }

    // ... (나머지 메서드)
    
    // Keep-alive / Heartbeat mechanism
     private val heartbeatHandler = android.os.Handler(android.os.Looper.getMainLooper())
     private val heartbeatRunnable = object : Runnable {
         override fun run() {
             if (isStreaming && !isIntentionalStop) {
                 // 서버 health check를 통해 실제 서버가 살아있는지 확인
                 checkServerHealth()
                 
                 // 3초마다 체크
                 heartbeatHandler.postDelayed(this, 3000)
             }
         }
     }
    
    private fun checkServerHealth() {
        // 백그라운드 스레드에서 서버 상태 체크
        Thread {
            try {
                // 저장된 서버 IP로 health check
                val prefs = getSharedPreferences("settings", Context.MODE_PRIVATE)
                val serverIp = prefs.getString("server_ip", "10.0.2.2") ?: "10.0.2.2"
                
                // RTMP 서버의 HTTP 포트로 요청 (Master는 8000 포트에서 HTTP 서버 운영)
                val url = java.net.URL("http://$serverIp:8000/health")
                val connection = url.openConnection() as java.net.HttpURLConnection
                connection.connectTimeout = 2000 // 2초 타임아웃
                connection.readTimeout = 2000
                connection.requestMethod = "GET"
                
                val responseCode = connection.responseCode
                
                if (responseCode == 200) {
                    // JSON 응답 파싱하여 stream_active 확인
                    val responseBody = connection.inputStream.bufferedReader().use { it.readText() }
                    connection.disconnect()
                    
                    try {
                        val json = org.json.JSONObject(responseBody)
                        val streamActive = json.optBoolean("stream_active", false)
                        
                        if (streamActive) {
                            // 서버도 살아있고 스트림도 활성화됨
                            Log.d(TAG, "💚 Heartbeat: Server healthy, stream active")
                        } else {
                            // 서버는 살아있지만 스트림이 비활성 상태
                            if (rtmpDisplay.isStreaming) {
                                Log.w(TAG, "⚠️ Server alive but stream inactive on server side, reconnecting...")
                                android.os.Handler(android.os.Looper.getMainLooper()).post {
                                    forceReconnect()
                                }
                            } else {
                                Log.w(TAG, "⚠️ Server alive but no stream (local also not streaming)")
                            }
                        }
                    } catch (e: Exception) {
                        Log.e(TAG, "Failed to parse health response: ${e.message}")
                    }
                } else {
                    connection.disconnect()
                    Log.w(TAG, "💔 Heartbeat: Server returned $responseCode")
                }
            } catch (e: Exception) {
                // 서버 연결 실패 = 서버가 죽었거나 재시작 중
                Log.w(TAG, "💔 Heartbeat: Server unreachable (${e.message})")
                // 서버가 죽었을 때는 일단 대기하고, 다음 heartbeat에서 다시 확인
                // 연결이 끊어졌다면 onDisconnect 콜백이 이미 처리함
            }
        }.start()
    }
    
    private fun forceReconnect() {
        if (!isStreaming || isIntentionalStop) {
            return
        }
        
        Log.w(TAG, "🔄 Force reconnecting (attempt #${retryCount + 1})...")
        
        retryCount++
        val delay = 2000L // 2초 대기 (서버 재시작 대기)
        
        updateNotification("서버 재연결 중... (${retryCount}회)")
        sendStatusBroadcast(STATUS_CONNECTING, "서버 재연결 중... (${retryCount}회)")
        
        // Use library's built-in reTry method which keeps MediaProjection alive
        // This calls disconnect(clear=false) internally, preserving the MediaProjection token
        try {
            Log.d(TAG, "🔄 Using library's reTry() to reconnect to $rtmpUrl")
            val reason = "Server stream inactive"
            rtmpDisplay.getStreamClient().reTry(delay, reason, rtmpUrl)
        } catch (e: Exception) {
            Log.e(TAG, "❌ Reconnection failed: ${e.message}", e)
            // Fallback: stop heartbeat and wait for manual restart
            stopHeartbeat()
        }
    }

    override fun onCreate() {
        super.onCreate()
        
        // 화면 정보 가져오기
        initScreenMetrics()
        
        // Notification 채널 생성
        createNotificationChannel()
        
        // RtmpDisplay 초기화
        rtmpDisplay = RtmpDisplay(baseContext, true, this)
        
        // Enable retry mechanism - CRITICAL for reconnection!
        rtmpDisplay.getStreamClient().setReTries(999) // Allow unlimited retries
        
        Log.d(TAG, "Service created")
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_UPDATE_SETTINGS) {
            handleSettingsUpdate(intent)
            return START_STICKY
        }

        val notification = createNotification("대기 중...")
        
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(
                NOTIFICATION_ID, 
                notification, 
                ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PROJECTION
            )
        } else {
            startForeground(NOTIFICATION_ID, notification)
        }

        Log.d(TAG, "🔍 onStartCommand called, intent: ${if (intent != null) "NOT NULL" else "NULL"}")
        
        intent?.let {
            Log.d(TAG, "🔍 Intent extras: ${it.extras?.keySet()?.joinToString()}")
            val resultCode = it.getIntExtra("resultCode", -1)
            Log.d(TAG, "🔍 Raw resultCode from intent: $resultCode (RESULT_OK = ${Activity.RESULT_OK})")
            
            val data = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                it.getParcelableExtra("data", Intent::class.java)
            } else {
                @Suppress("DEPRECATION")
                it.getParcelableExtra<Intent>("data")
            }
            Log.d(TAG, "🔍 Data intent: ${if (data != null) "NOT NULL" else "NULL"}")
            
            // 저장된 IP 불러오기
            val prefs = getSharedPreferences("settings", Context.MODE_PRIVATE)
            val serverIp = prefs.getString("server_ip", "192.168.0.12") ?: "192.168.0.12"
            
            // RTMP URL 설정
            rtmpUrl = "rtmp://$serverIp:1935/live/stream"
            
            Log.i(TAG, "════════════════════════════════════════")
            Log.i(TAG, "🎬 Screen Capture Service Starting")
            Log.i(TAG, "📍 Server IP: $serverIp")
            Log.i(TAG, "🔗 RTMP URL: $rtmpUrl")
            Log.i(TAG, "════════════════════════════════════════")
            Log.d(TAG, "RTMP URL: $rtmpUrl")
            Log.d(TAG, "🔍 resultCode: $resultCode, data: ${if (data != null) "not null" else "NULL"}")
            
            if (resultCode == Activity.RESULT_OK && data != null) {
                // MediaProjection 정보 저장
                savedResultCode = resultCode
                savedData = data
                Log.i(TAG, "✅ Starting stream with valid data")
                startStream(resultCode, data)
            } else {
                Log.e(TAG, "❌ Cannot start stream - resultCode: $resultCode (expected: ${Activity.RESULT_OK}), data: ${data == null}")
            }
        }

        return START_STICKY
    }

    private fun handleSettingsUpdate(intent: Intent) {
        if (!isStreaming) return
        
        Log.i(TAG, "🔄 Received settings update request")
        
        val newBitrateIndex = intent.getIntExtra(EXTRA_BITRATE, -1)
        val newFpsIndex = intent.getIntExtra(EXTRA_FPS, -1)
        val newResIndex = intent.getIntExtra(EXTRA_RESOLUTION_INDEX, -1)
        val newUseNative = intent.getBooleanExtra(EXTRA_USE_NATIVE_RES, false)
        
        // Check current settings (from prefs) to see what changed
        val prefs = getSharedPreferences("streaming_settings", Context.MODE_PRIVATE)
        val currentBitrateIndex = prefs.getInt("bitrate", 2)
        val currentFpsIndex = prefs.getInt("fps", 2)
        val currentResIndex = prefs.getInt("resolution", 0)
        val currentUseNative = prefs.getBoolean("use_native_res", false)
        
        // 1. Bitrate Change (Real-time)
        if (newBitrateIndex != -1 && newBitrateIndex != currentBitrateIndex) {
            val bitrate = getBitrateValue(newBitrateIndex)
            Log.i(TAG, "📶 Changing Bitrate: ${bitrate / 1024} kbps")
            
            try {
                rtmpDisplay.setVideoBitrateOnFly(bitrate)
                prefs.edit().putInt("bitrate", newBitrateIndex).apply()
                Toast.makeText(this, "비트레이트 변경됨: ${bitrate / 1024} kbps", Toast.LENGTH_SHORT).show()
            } catch (e: Exception) {
                Log.e(TAG, "Failed to change bitrate: ${e.message}")
            }
        }
        
        // 2. Resolution or FPS Change (Requires Restart)
        val resChanged = (newResIndex != -1 && newResIndex != currentResIndex) || (newUseNative != currentUseNative)
        val fpsChanged = (newFpsIndex != -1 && newFpsIndex != currentFpsIndex)
        
        if (resChanged || fpsChanged) {
            Log.i(TAG, "🔄 Resolution/FPS changed. Restart required.")
            
            // Save new settings
            prefs.edit().apply {
                if (newResIndex != -1) putInt("resolution", newResIndex)
                if (newFpsIndex != -1) putInt("fps", newFpsIndex)
                putBoolean("use_native_res", newUseNative)
                apply()
            }
            
            // Auto Restart Logic
            Toast.makeText(this, "해상도 변경을 위해 재시작합니다...", Toast.LENGTH_SHORT).show()
            
            // 안전하게 재시작
            restartStreamWithNewSettings()
        }
    }
    
    private fun getBitrateValue(index: Int): Int {
        return when (index) {
            0 -> 5000 * 1024
            1 -> 8000 * 1024
            2 -> 10000 * 1024
            3 -> 15000 * 1024
            4 -> 20000 * 1024
            5 -> 25000 * 1024
            6 -> 30000 * 1024
            else -> 10000 * 1024
        }
    }

    private fun initScreenMetrics() {
        val windowManager = getSystemService(Context.WINDOW_SERVICE) as WindowManager
        val metrics = DisplayMetrics()
        
        // Service에서는 display를 직접 가져올 수 없으므로 WindowManager 사용
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            val display = windowManager.defaultDisplay
            @Suppress("DEPRECATION")
            display?.getRealMetrics(metrics)
        } else {
            @Suppress("DEPRECATION")
            windowManager.defaultDisplay.getRealMetrics(metrics)
        }
        
        screenWidth = metrics.widthPixels
        screenHeight = metrics.heightPixels
        screenDensity = metrics.densityDpi
        
        Log.d(TAG, "Screen: ${screenWidth}x${screenHeight}, DPI: $screenDensity")
    }

    private fun startStream(resultCode: Int, data: Intent, isReconnection: Boolean = false) {
        if (isStreaming) {
            Log.w(TAG, "Already streaming")
            return
        }
        
        // MediaProjection 정보 저장 (재연결 시 사용) - 첫 시작 시에만
        if (!isReconnection) {
            savedResultCode = resultCode
            savedData = data
            Log.d(TAG, "💾 Saved intent data for reconnection (resultCode: $resultCode)")
        }
        
        try {
            // 저장된 설정 불러오기
            val streamingPrefs = getSharedPreferences("streaming_settings", Context.MODE_PRIVATE)
            val useNativeRes = streamingPrefs.getBoolean("use_native_res", false)
            
            // 서버 IP 불러오기 (크롭 정보 전송용)
            val prefs = getSharedPreferences("settings", Context.MODE_PRIVATE)
            val serverIp = prefs.getString("server_ip", "192.168.0.12") ?: "192.168.0.12"
            
            // 해상도 설정
            val (width, height) = if (useNativeRes) {
                // 기기 전체화면 (Native) 사용
                // 인코더는 보통 짝수 해상도를 선호하므로 2의 배수로 보정
                val nativeWidth = (screenWidth / 2) * 2
                val nativeHeight = (screenHeight / 2) * 2
                Log.i(TAG, "📺 Using Native Resolution: ${nativeWidth}x${nativeHeight} (Screen: ${screenWidth}x${screenHeight})")
                Pair(nativeWidth, nativeHeight)
            } else {
                // 표준 16:9 비율 사용 - 중앙 크롭으로 송출
                // 전체 화면을 캡처하되, 인코더가 16:9 해상도로 중앙 크롭하여 송출
                val resolutionIndex = streamingPrefs.getInt("resolution", 0)
                val (targetWidth, targetHeight) = when (resolutionIndex) {
                    0 -> Pair(1920, 1080)  // FHD (기본값)
                    1 -> Pair(2560, 1440)  // QHD
                    2 -> Pair(3840, 2160)  // 4K
                    else -> Pair(1920, 1080)
                }
                Log.i(TAG, "📺 Using 16:9 Mode: ${targetWidth}x${targetHeight} (Screen: ${screenWidth}x${screenHeight})")
                Pair(targetWidth, targetHeight)
            }
            
            // FPS 설정
            val fpsIndex = streamingPrefs.getInt("fps", 2) // 기본 30fps
            val fps = when (fpsIndex) {
                0 -> 15
                1 -> 24
                2 -> 30  // 기본값
                3 -> 60
                else -> 30
            }
            
            // 비트레이트 설정
            val bitrateIndex = streamingPrefs.getInt("bitrate", 2) // 기본 10.0 Mbps
            val bitrate = when (bitrateIndex) {
                0 -> 5000 * 1024   // 5.0 Mbps
                1 -> 8000 * 1024   // 8.0 Mbps
                2 -> 10000 * 1024  // 10.0 Mbps (기본값)
                3 -> 15000 * 1024  // 15.0 Mbps
                4 -> 20000 * 1024  // 20.0 Mbps
                5 -> 25000 * 1024  // 25.0 Mbps
                6 -> 30000 * 1024  // 30.0 Mbps
                else -> 10000 * 1024
            }
            
            val audioEnabled = streamingPrefs.getBoolean("audio_enabled", true)
            val rotation = 0
            
             // 키프레임 간격 설정 (초 단위 - Int)
             // Ultra-low latency: I-frame을 자주 생성하여 최대 지연 최소화
             // 정지된 화면도 계속 스트리밍하려면 매우 짧아야 함
             val iFrameInterval = 1 // 1초마다 I-frame (정지화면도 계속 송출)
            
            Log.i(TAG, "📊 Streaming Settings:")
            Log.i(TAG, "   Resolution: ${width}x${height}")
            Log.i(TAG, "   FPS: $fps")
            Log.i(TAG, "   Bitrate: ${bitrate / 1024} kbps")
            Log.i(TAG, "   Keyframe Interval: ${iFrameInterval}s")
            Log.i(TAG, "   Audio: ${if (audioEnabled) "Enabled" else "Disabled"}")
            
            // 오디오 및 비디오 준비
            // 전체 화면을 캡처하되, 16:9 모드일 때는 백엔드에서 크롭하도록 크롭 정보 전송
            val audioReady = if (audioEnabled) rtmpDisplay.prepareAudio() else true
            
            // 전체 화면 해상도로 캡처 (백엔드에서 크롭)
            val captureWidth = screenWidth
            val captureHeight = screenHeight
            
            val videoReady = rtmpDisplay.prepareVideo(
                captureWidth, 
                captureHeight, 
                fps, 
                bitrate, 
                rotation, 
                iFrameInterval,  // screenDensity 대신 키프레임 간격 사용
                // CRITICAL: 정지화면 지원을 위해 H264 프로파일 설정
                // Baseline 프로파일은 I-frame을 강제로 계속 생성함
                // 이렇게 하면 정지화면에서도 데이터가 계속 전송됨
                // Note: 이 파라미터가 없으면 기본 API 사용
            )
            
            if (!audioReady || !videoReady) {
                Log.e(TAG, "Failed to prepare audio or video")
                updateNotification("준비 실패")
                return
            }
            
            Log.i(TAG, "✅ Video encoder ready (keyframe interval: ${iFrameInterval}s for static screen support)")
            
            // MediaProjection 설정
            // 재연결 시에도 MediaProjection을 다시 설정해야 함 (rtmpDisplay가 내부적으로 해제할 수 있음)
            rtmpDisplay.setIntentResult(resultCode, data)
            if (isReconnection) {
                Log.d(TAG, "🔄 Reinitializing MediaProjection for reconnection")
            } else {
                Log.d(TAG, "🔑 MediaProjection initialized")
            }
            
            // RTMP 스트리밍 시작
            Log.i(TAG, "📡 Starting stream to: $rtmpUrl")
            sendStatusBroadcast(STATUS_STARTING, "스트리밍 준비 완료. 서버 연결 중...", rtmpUrl)
            
            isIntentionalStop = false // Reset intentional stop flag
            retryCount = 0            // Reset retry counter
            
            rtmpDisplay.startStream(rtmpUrl)
            isStreaming = true
            
            // Start performance monitoring
            startPerformanceMonitoring()
            
            // Start heartbeat monitoring
            startHeartbeat()
            
            // CRITICAL: Start keyframe generator for static screen support
            startKeyframeGenerator()
            
            // Show Floating Control
            showFloatingControl()
            
            updateNotification("스트리밍 중...")
            Log.i(TAG, "✅ Stream command sent to: $rtmpUrl")
            
        } catch (e: Exception) {
            Log.e(TAG, "❌ Error starting stream: ${e.message}", e)
            updateNotification("시작 실패")
            sendStatusBroadcast(STATUS_FAILED, "스트리밍 시작 실패: ${e.message}")
        }
    }

    private fun stopStream() {
        if (!isStreaming) return
        
        isIntentionalStop = true // Mark as intentional stop
        reconnectHandler.removeCallbacks(reconnectRunnable) // Cancel any pending reconnects
        stopHeartbeat() // Stop heartbeat monitoring
        stopKeyframeGenerator() // Stop keyframe generator
        
        try {
            // Stop performance monitoring
            stopPerformanceMonitoring()
            
            // Remove Floating Control
            removeFloatingControl()
            
            if (rtmpDisplay.isStreaming) {
                rtmpDisplay.stopStream()
            }
            isStreaming = false
            updateNotification("스트리밍 중지됨")
            Log.i(TAG, "Streaming stopped")
        } catch (e: Exception) {
            Log.e(TAG, "Error stopping stream: ${e.message}", e)
        }
    }
    
    // 해상도 변경 시 안전하게 재시작
    private fun restartStreamWithNewSettings() {
        try {
            // MediaProjection 정보 확인
            if (savedResultCode == -1 || savedData == null) {
                Log.e(TAG, "❌ Cannot restart: MediaProjection info not available")
                Toast.makeText(this, "재시작 실패: 화면 캡처 정보가 없습니다", Toast.LENGTH_SHORT).show()
                return
            }
            
            // 현재 스트림 중지
            val wasStreaming = isStreaming
            if (wasStreaming) {
                try {
                    if (rtmpDisplay.isStreaming) {
                        rtmpDisplay.stopStream()
                    }
                    isStreaming = false
                } catch (e: Exception) {
                    Log.w(TAG, "Error stopping stream during restart: ${e.message}")
                }
            }
            
            // 짧은 딜레이 후 재시작 (인코더 정리 시간)
            android.os.Handler(Looper.getMainLooper()).postDelayed({
                try {
                    // 새로운 설정으로 스트림 시작
                    startStream(savedResultCode, savedData!!)
                    Log.i(TAG, "✅ Stream restarted with new settings")
                } catch (e: Exception) {
                    Log.e(TAG, "❌ Error restarting stream: ${e.message}", e)
                    Toast.makeText(this, "재시작 실패: ${e.message}", Toast.LENGTH_SHORT).show()
                    updateNotification("재시작 실패")
                }
            }, 500) // 500ms 딜레이로 충분
            
        } catch (e: Exception) {
            Log.e(TAG, "❌ Error in restartStreamWithNewSettings: ${e.message}", e)
            Toast.makeText(this, "재시작 중 오류 발생", Toast.LENGTH_SHORT).show()
        }
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "화면 스트리밍 서비스",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "실시간으로 화면을 스트리밍합니다"
            }

            val notificationManager = getSystemService(NotificationManager::class.java)
            notificationManager.createNotificationChannel(channel)
        }
    }

    private fun createNotification(status: String): Notification {
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("화면 스트리밍")
            .setContentText(status)
            .setSmallIcon(R.drawable.ic_launcher)
            .setOngoing(true)
            .build()
    }

    private fun updateNotification(status: String) {
        val notificationManager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        notificationManager.notify(NOTIFICATION_ID, createNotification(status))
    }

    override fun onDestroy() {
        stopStream()
        stopHeartbeat() // Ensure heartbeat is stopped
        removeFloatingControl() // Ensure floating control is removed
        super.onDestroy()
        Log.d(TAG, "Service destroyed")
    }

    override fun onBind(intent: Intent?): IBinder? = null

    // 상태 브로드캐스트 전송
    private fun sendStatusBroadcast(status: String, message: String, url: String = rtmpUrl) {
        val intent = Intent(ACTION_CONNECTION_STATUS).apply {
            putExtra(EXTRA_STATUS, status)
            putExtra(EXTRA_MESSAGE, message)
            putExtra(EXTRA_URL, url)
        }
        sendBroadcast(intent)
        Log.d(TAG, "📡 Broadcast sent: $status - $message")
    }

    // ConnectChecker 인터페이스 구현
    override fun onConnectionStarted(url: String) {
        Log.d(TAG, "🔄 Connection starting to: $url")
        updateNotification("연결 중...")
        sendStatusBroadcast(STATUS_CONNECTING, "서버에 연결 중...", url)
    }

    override fun onConnectionSuccess() {
        Log.d(TAG, "✅ Connection success")
        retryCount = 0 // Reset retry count on success
        reconnectHandler.removeCallbacks(reconnectRunnable)
        
        updateNotification("연결 성공 - 스트리밍 중")
        sendStatusBroadcast(STATUS_CONNECTED, "연결 성공! 스트리밍 중")
        
        // Restart heartbeat after successful connection
        startHeartbeat()
    }

    override fun onConnectionFailed(reason: String) {
        Log.e(TAG, "❌ Connection failed: $reason")
        
        if (isIntentionalStop) {
            Log.d(TAG, "Connection failed but it was intentional stop. Ignoring.")
            return
        }

        // Aggressive Reconnect Logic - 계속 재시도
        retryCount++
        val delay = calculateRetryDelay(retryCount)
        
        updateNotification("연결 실패. ${delay/1000}초 후 재시도 (${retryCount}회)")
        sendStatusBroadcast(STATUS_CONNECTING, "서버 연결 실패. ${delay/1000}초 후 재시도 중... (${retryCount}회)")
        
        Log.w(TAG, "🔄 Scheduling reconnect attempt #$retryCount in ${delay}ms")
        reconnectHandler.postDelayed(reconnectRunnable, delay)
    }
    
    private fun calculateRetryDelay(attempt: Int): Long {
        // Faster reconnection: 2s, 3s, 5s, 5s(max)... - 빠르게 재시도
        return when {
            attempt == 1 -> 2000L  // 첫 시도: 2초
            attempt == 2 -> 3000L  // 두 번째: 3초
            else -> 5000L          // 이후: 5초마다 계속
        }
    }
    
    // Heartbeat (Keep-alive) methods
    private fun startHeartbeat() {
        stopHeartbeat() // Stop any existing heartbeat
        Log.i(TAG, "💚 Starting heartbeat monitoring (3s interval)")
        heartbeatHandler.postDelayed(heartbeatRunnable, 3000) // First check after 3 seconds
    }
    
    private fun stopHeartbeat() {
        heartbeatHandler.removeCallbacks(heartbeatRunnable)
        Log.i(TAG, "💔 Heartbeat monitoring stopped")
    }
    
    // Keyframe generator for static screen support
    private fun startKeyframeGenerator() {
        stopKeyframeGenerator()
        Log.i(TAG, "🔑 Starting keyframe generator (2s interval) for static screen support")
        keyframeHandler.postDelayed(keyframeRunnable, 2000)
    }
    
    private fun stopKeyframeGenerator() {
        keyframeHandler.removeCallbacks(keyframeRunnable)
        Log.i(TAG, "🔑 Keyframe generator stopped")
    }

    override fun onNewBitrate(bitrate: Long) {
        // Track actual bitrate
        val currentTime = System.currentTimeMillis()
        frameCount++
        
        // Calculate frame timing
        if (lastFrameTime > 0) {
            val frameInterval = currentTime - lastFrameTime
            frameTimeList.add(frameInterval)
            
            // Keep only last 60 frames for rolling average
            if (frameTimeList.size > 60) {
                frameTimeList.removeAt(0)
            }
        }
        lastFrameTime = currentTime
    }

    override fun onDisconnect() {
        Log.d(TAG, "🔌 Disconnected from server")
        
        if (isIntentionalStop) {
            updateNotification("연결 끊김")
            sendStatusBroadcast(STATUS_DISCONNECTED, "서버와 연결이 끊어졌습니다")
            return
        }
        
        // Unexpected disconnect - 서버가 죽었거나 재시작 중
        Log.w(TAG, "⚠️ Unexpected disconnect! Will attempt to reconnect...")
        retryCount++
        
        // 서버가 재시작 중일 수 있으므로 조금 더 대기
        val delay = 3000L // 3초 대기 (서버 재시작 시간 고려)
        
        updateNotification("서버 재연결 대기 중... (${delay/1000}초)")
        sendStatusBroadcast(STATUS_CONNECTING, "서버 재시작 감지. ${delay/1000}초 후 재연결...")
        
        // Use library's built-in reTry method which keeps MediaProjection alive
        try {
            Log.d(TAG, "🔄 Using library's reTry() to reconnect to $rtmpUrl after disconnect")
            val reason = "Unexpected disconnect"
            rtmpDisplay.getStreamClient().reTry(delay, reason, rtmpUrl)
        } catch (e: Exception) {
            Log.e(TAG, "❌ Reconnection attempt failed: ${e.message}", e)
            // Fallback: stop heartbeat and wait for manual restart
            stopHeartbeat()
        }
    }

    override fun onAuthError() {
        Log.e(TAG, "🔒 Authentication error")
        updateNotification("인증 오류")
        sendStatusBroadcast(STATUS_FAILED, "서버 인증 오류")
    }

    override fun onAuthSuccess() {
        Log.d(TAG, "🔓 Authentication success")
    }
    
    
    // --- Floating Control Methods ---

    private fun showFloatingControl() {
        removeFloatingControl()

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M && !android.provider.Settings.canDrawOverlays(this)) {
            return
        }

        try {
            windowManager = getSystemService(WINDOW_SERVICE) as WindowManager
            
            val type = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
            } else {
                @Suppress("DEPRECATION")
                WindowManager.LayoutParams.TYPE_PHONE
            }

            // 1. Layout Params 설정 (터치 이벤트 처리를 위해 초기엔 작게)
            floatingLayoutParams = WindowManager.LayoutParams(
                WindowManager.LayoutParams.WRAP_CONTENT,
                WindowManager.LayoutParams.WRAP_CONTENT,
                type,
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE,
                PixelFormat.TRANSLUCENT
            ).apply {
                gravity = Gravity.TOP or Gravity.START
                x = 20
                y = 200
            }

            // 2. 메인 컨테이너 생성
            floatingLayout = FrameLayout(this)
            
            // 3. 메뉴 컨테이너 (처음엔 숨김)
            menuContainer = FrameLayout(this).apply {
                visibility = View.GONE
            }
            floatingLayout?.addView(menuContainer, FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
            ))

            // 4. 메인 볼 생성
            val ballSize = (60 * resources.displayMetrics.density).toInt()
            mainBall = ImageView(this).apply {
                setImageResource(R.drawable.ic_launcher) // 앱 아이콘
                background = createStatusBackground(COLOR_NORMAL) // 초기: 초록색 테두리
                setPadding(15, 15, 15, 15)
                elevation = 10f
                alpha = 0.6f // 기본 반투명
            }
            
            val ballParams = FrameLayout.LayoutParams(ballSize, ballSize)
            floatingLayout?.addView(mainBall, ballParams)

            // 5. 메뉴 아이템 생성 (설정, 중지, 닫기)
            createMenuItem("설정", 1, ballSize) { showOverlaySettingsDialog() }
            createMenuItem("중지", 2, ballSize) { 
                stopStream()
                // 중지 후 앱으로 돌아가기 위한 인텐트 발송 등 추가 가능
            }
            createMenuItem("닫기", 3, ballSize) { toggleMenu(false) }

            // 6. 터치 리스너 (드래그 & 클릭)
            mainBall?.setOnTouchListener(object : View.OnTouchListener {
                private var initialX = 0
                private var initialY = 0
                private var initialTouchX = 0f
                private var initialTouchY = 0f
                private var isClick = false

                override fun onTouch(v: View, event: MotionEvent): Boolean {
                    when (event.action) {
                        MotionEvent.ACTION_DOWN -> {
                            initialX = floatingLayoutParams!!.x
                            initialY = floatingLayoutParams!!.y
                            initialTouchX = event.rawX
                            initialTouchY = event.rawY
                            isClick = true
                            return true
                        }
                        MotionEvent.ACTION_MOVE -> {
                            val dx = (event.rawX - initialTouchX).toInt()
                            val dy = (event.rawY - initialTouchY).toInt()
                            
                            if (abs(dx) > 10 || abs(dy) > 10) {
                                isClick = false
                                if (isMenuExpanded) toggleMenu(false) // 드래그 시 메뉴 닫기
                            }

                            floatingLayoutParams!!.x = initialX + dx
                            floatingLayoutParams!!.y = initialY + dy
                            windowManager?.updateViewLayout(floatingLayout, floatingLayoutParams)
                            return true
                        }
                        MotionEvent.ACTION_UP -> {
                            if (isClick) {
                                toggleMenu(!isMenuExpanded) // 토글
                            }
                            return true
                        }
                    }
                    return false
                }
            })

            windowManager?.addView(floatingLayout, floatingLayoutParams)
            
        } catch (e: Exception) {
            Log.e(TAG, "Error showing floating control: ${e.message}", e)
        }
    }

    private fun createStatusBackground(strokeColor: Int): GradientDrawable {
        return GradientDrawable().apply {
            shape = GradientDrawable.OVAL
            setColor(Color.parseColor("#44000000")) // 배경: 반투명 검정
            setStroke(8, strokeColor) // 테두리: 상태색 (두께 8)
        }
    }

    private fun createMenuItem(label: String, index: Int, ballSize: Int, onClick: () -> Unit) {
        // 간단한 텍스트 버튼 생성
        val btnSize = (50 * resources.displayMetrics.density).toInt()
        val btn = TextView(this).apply {
            text = label
            setTextColor(Color.WHITE)
            gravity = Gravity.CENTER
            textSize = 12f
            background = GradientDrawable().apply {
                shape = GradientDrawable.OVAL
                setColor(Color.parseColor("#99000000")) // 더 진한 반투명
                setStroke(2, Color.WHITE)
            }
            setOnClickListener { 
                onClick()
                toggleMenu(false)
            }
        }

        val params = FrameLayout.LayoutParams(btnSize, btnSize)
        // 위치 계산 (링 형태 배치 - 여기선 간단히 우측으로 나열)
        // 실제 링 배치는 삼각함수 필요. 일단 우측, 우하단, 하단으로 배치
        val distance = ballSize.toFloat() * 1.2f
        val angle = when(index) {
            1 -> -45.0 // 우상단
            2 -> 0.0   // 우측
            else -> 45.0 // 우하단
        }
        val rad = Math.toRadians(angle)
        
        // 초기엔 메인 볼 뒤에 숨김 (Translation으로 이동)
        btn.translationX = 0f
        btn.translationY = 0f
        btn.alpha = 0f
        
        // 태그에 목표 위치 저장
        btn.tag = PointF((cos(rad) * distance).toFloat(), (sin(rad) * distance).toFloat())
        
        menuContainer?.addView(btn, params)
    }
    
    private fun toggleMenu(expand: Boolean) {
        isMenuExpanded = expand
        val container = menuContainer ?: return
        
        if (expand) {
            container.visibility = View.VISIBLE
            // 펼치기 애니메이션
            for (i in 0 until container.childCount) {
                val child = container.getChildAt(i)
                val target = child.tag as PointF
                child.animate()
                    .translationX(target.x)
                    .translationY(target.y)
                    .alpha(1f)
                    .setDuration(200)
                    .start()
            }
        } else {
            // 접기 애니메이션
            for (i in 0 until container.childCount) {
                val child = container.getChildAt(i)
                child.animate()
                    .translationX(0f)
                    .translationY(0f)
                    .alpha(0f)
                    .setDuration(200)
                    .withEndAction { if (i == container.childCount - 1) container.visibility = View.GONE }
                    .start()
            }
        }
    }

    private fun updateStatusColor(status: String) {
        val color = when (status) {
            STATUS_CONNECTED -> COLOR_NORMAL
            STATUS_CONNECTING, STATUS_STARTING -> COLOR_WARNING
            else -> COLOR_ERROR
        }
        
        if (currentStatusColor != color) {
            currentStatusColor = color
            mainBall?.background = createStatusBackground(color)
            mainBall?.invalidate()
        }
    }

    private fun removeFloatingControl() {
        if (floatingLayout != null) {
            try {
                windowManager?.removeView(floatingLayout)
                floatingLayout = null
                mainBall = null
                menuContainer = null
            } catch (e: Exception) {
                Log.e(TAG, "Error removing floating control: ${e.message}")
            }
        }
    }

    private fun showOverlaySettingsDialog() {
        // Service Context에서 Dialog를 띄우기 위해 ThemeWrapper 사용
        // 안전하게 시스템 기본 Dialog 테마 사용
        val contextThemeWrapper = ContextThemeWrapper(this, androidx.appcompat.R.style.Theme_AppCompat_Light_Dialog)
        val dialogView = LayoutInflater.from(contextThemeWrapper).inflate(R.layout.dialog_streaming_options, null)

        // UI 요소 찾기
        val rgAspectRatio = dialogView.findViewById<RadioGroup>(R.id.rg_aspect_ratio)
        val rbAspect16_9 = dialogView.findViewById<RadioButton>(R.id.rb_aspect_16_9)
        val rbAspectDevice = dialogView.findViewById<RadioButton>(R.id.rb_aspect_device)
        val resolutionSpinner = dialogView.findViewById<Spinner>(R.id.spinner_resolution)
        val fpsSpinner = dialogView.findViewById<Spinner>(R.id.fpsSpinner)
        val bitrateSpinner = dialogView.findViewById<Spinner>(R.id.bitrateSpinner)
        val audioSwitch = dialogView.findViewById<SwitchCompat>(R.id.audioSwitch)
        val autoReconnectSwitch = dialogView.findViewById<SwitchCompat>(R.id.autoReconnectSwitch)

        // 어댑터 설정 (Context 주의)
        val resolutions = arrayOf("FHD (1920x1080)", "QHD (2560x1440)", "4K (3840x2160)")
        resolutionSpinner.adapter = ArrayAdapter(contextThemeWrapper, android.R.layout.simple_spinner_dropdown_item, resolutions)

        val fpsOptions = arrayOf("15 fps", "24 fps", "30 fps", "60 fps")
        fpsSpinner.adapter = ArrayAdapter(contextThemeWrapper, android.R.layout.simple_spinner_dropdown_item, fpsOptions)

        val bitrateOptions = arrayOf("5.0 Mbps", "8.0 Mbps", "10.0 Mbps", "15.0 Mbps", "20.0 Mbps", "25.0 Mbps", "30.0 Mbps")
        bitrateSpinner.adapter = ArrayAdapter(contextThemeWrapper, android.R.layout.simple_spinner_dropdown_item, bitrateOptions)

        // 현재 설정 불러오기
        val prefs = getSharedPreferences("streaming_settings", Context.MODE_PRIVATE)
        val useNativeRes = prefs.getBoolean("use_native_res", false)

        if (useNativeRes) {
            rbAspectDevice.isChecked = true
            resolutionSpinner.isEnabled = false
            resolutionSpinner.alpha = 0.5f
        } else {
            rbAspect16_9.isChecked = true
            resolutionSpinner.isEnabled = true
            resolutionSpinner.alpha = 1.0f
        }

        rgAspectRatio.setOnCheckedChangeListener { _, checkedId ->
            if (checkedId == R.id.rb_aspect_device) {
                resolutionSpinner.isEnabled = false
                resolutionSpinner.alpha = 0.5f
            } else {
                resolutionSpinner.isEnabled = true
                resolutionSpinner.alpha = 1.0f
            }
        }

        resolutionSpinner.setSelection(prefs.getInt("resolution", 0))
        fpsSpinner.setSelection(prefs.getInt("fps", 2))
        bitrateSpinner.setSelection(prefs.getInt("bitrate", 1))
        audioSwitch.isChecked = prefs.getBoolean("audio_enabled", true)
        autoReconnectSwitch.isChecked = prefs.getBoolean("auto_reconnect", true)

        // Dialog 생성 (TYPE_APPLICATION_OVERLAY 필수)
        val dialog = AlertDialog.Builder(contextThemeWrapper)
            .setView(dialogView)
            .create()

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            dialog.window?.setType(WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY)
        } else {
            @Suppress("DEPRECATION")
            dialog.window?.setType(WindowManager.LayoutParams.TYPE_PHONE)
        }

        // 저장 버튼
        dialogView.findViewById<Button>(R.id.saveButton).setOnClickListener {
            val newUseNative = rbAspectDevice.isChecked
            val newResIndex = resolutionSpinner.selectedItemPosition
            val newFpsIndex = fpsSpinner.selectedItemPosition
            val newBitrateIndex = bitrateSpinner.selectedItemPosition

            // 즉시 설정 변경 적용 (Service 내부이므로 직접 호출 가능)
            handleInternalSettingsUpdate(newUseNative, newResIndex, newFpsIndex, newBitrateIndex)
            
            // Prefs 저장
            prefs.edit().apply {
                putBoolean("use_native_res", newUseNative)
                putInt("resolution", newResIndex)
                putInt("fps", newFpsIndex)
                putInt("bitrate", newBitrateIndex)
                putBoolean("audio_enabled", audioSwitch.isChecked)
                putBoolean("auto_reconnect", autoReconnectSwitch.isChecked)
                apply()
            }
            
            Toast.makeText(this, "설정이 변경되었습니다", Toast.LENGTH_SHORT).show()
            dialog.dismiss()
        }

        // 취소 버튼
        dialogView.findViewById<Button>(R.id.cancelButton).setOnClickListener {
            dialog.dismiss()
        }

        dialog.show()
    }
    
    private fun handleInternalSettingsUpdate(newUseNative: Boolean, newResIndex: Int, newFpsIndex: Int, newBitrateIndex: Int) {
        // Reuse the logic from handleSettingsUpdate but called directly
        val prefs = getSharedPreferences("streaming_settings", Context.MODE_PRIVATE)
        val currentBitrateIndex = prefs.getInt("bitrate", 2)
        val currentFpsIndex = prefs.getInt("fps", 2)
        val currentResIndex = prefs.getInt("resolution", 0)
        val currentUseNative = prefs.getBoolean("use_native_res", false)
        
        // 1. Bitrate Change
        if (newBitrateIndex != currentBitrateIndex) {
            val bitrate = getBitrateValue(newBitrateIndex)
            Log.i(TAG, "📶 Changing Bitrate: ${bitrate / 1024} kbps")
            try {
                rtmpDisplay.setVideoBitrateOnFly(bitrate)
            } catch (e: Exception) {
                Log.e(TAG, "Failed to change bitrate: ${e.message}")
            }
        }
        
        // 2. Resolution/FPS Change
        val resChanged = (newResIndex != currentResIndex) || (newUseNative != currentUseNative)
        val fpsChanged = (newFpsIndex != currentFpsIndex)
        
        if (resChanged || fpsChanged) {
            Log.i(TAG, "🔄 Settings changed. Restarting stream...")
            Toast.makeText(this, "설정 적용을 위해 재시작합니다...", Toast.LENGTH_SHORT).show()
            
            // Save prefs FIRST so restart picks them up
             prefs.edit().apply {
                putBoolean("use_native_res", newUseNative)
                putInt("resolution", newResIndex)
                putInt("fps", newFpsIndex)
                apply()
            }

            // 안전하게 재시작
            restartStreamWithNewSettings()
        }
    }
    
    // Performance monitoring methods
    private fun startPerformanceMonitoring() {
        frameCount = 0
        droppedFrames = 0
        lastFrameTime = System.currentTimeMillis()
        lastStatsTime = System.currentTimeMillis()
        totalEncodingTime = 0L
        encodingCount = 0
        frameTimeList.clear()
        
        // Log performance stats every 5 seconds
        performanceHandler.postDelayed(object : Runnable {
            override fun run() {
                if (isStreaming) {
                    logPerformanceStats()
                    performanceHandler.postDelayed(this, 5000)
                }
            }
        }, 5000)
        
        Log.i(TAG, "📊 Performance monitoring started")
    }
    
    private fun stopPerformanceMonitoring() {
        performanceHandler.removeCallbacksAndMessages(null)
        logPerformanceStats() // Final stats
        Log.i(TAG, "📊 Performance monitoring stopped")
    }
    
    private fun logPerformanceStats() {
        val currentTime = System.currentTimeMillis()
        val elapsedSeconds = (currentTime - lastStatsTime) / 1000.0
        
        if (elapsedSeconds < 0.1) return // Skip if too soon
        
        val actualFps = frameCount / elapsedSeconds
        val avgFrameInterval = if (frameTimeList.isNotEmpty()) {
            frameTimeList.average()
        } else {
            0.0
        }
        
        val minFrameInterval = frameTimeList.minOrNull() ?: 0L
        val maxFrameInterval = frameTimeList.maxOrNull() ?: 0L
        
        // Check for frame drops (intervals > 2x expected)
        val streamingPrefs = getSharedPreferences("streaming_settings", Context.MODE_PRIVATE)
        val fpsIndex = streamingPrefs.getInt("fps", 2)
        val targetFps = when (fpsIndex) {
            0 -> 15
            1 -> 24
            2 -> 30
            3 -> 60
            else -> 30
        }
        val expectedInterval = 1000.0 / targetFps
        val droppedInPeriod = frameTimeList.count { it > expectedInterval * 2 }
        
        // Memory usage
        val runtime = Runtime.getRuntime()
        val usedMemoryMB = (runtime.totalMemory() - runtime.freeMemory()) / (1024 * 1024)
        val maxMemoryMB = runtime.maxMemory() / (1024 * 1024)
        
        Log.i(TAG, "═══════════════════════════════════════════════════════")
        Log.i(TAG, "📊 PERFORMANCE STATS (${elapsedSeconds.toInt()}s window)")
        Log.i(TAG, "═══════════════════════════════════════════════════════")
        Log.i(TAG, "🎬 Frame Rate:")
        Log.i(TAG, "   Target FPS: $targetFps")
        Log.i(TAG, "   Actual FPS: %.2f".format(actualFps))
        Log.i(TAG, "   Total Frames: $frameCount")
        Log.i(TAG, "   Frame Drop Rate: %.1f%%".format((droppedInPeriod.toFloat() / frameTimeList.size) * 100))
        Log.i(TAG, "")
        Log.i(TAG, "⏱️  Frame Timing:")
        Log.i(TAG, "   Expected Interval: %.1f ms".format(expectedInterval))
        Log.i(TAG, "   Avg Interval: %.1f ms".format(avgFrameInterval))
        Log.i(TAG, "   Min Interval: $minFrameInterval ms")
        Log.i(TAG, "   Max Interval: $maxFrameInterval ms")
        Log.i(TAG, "")
        Log.i(TAG, "💾 Memory Usage:")
        Log.i(TAG, "   Used: $usedMemoryMB MB")
        Log.i(TAG, "   Max: $maxMemoryMB MB")
        Log.i(TAG, "   Usage: %.1f%%".format((usedMemoryMB.toFloat() / maxMemoryMB) * 100))
        Log.i(TAG, "")
        Log.i(TAG, "📡 Stream Status:")
        Log.i(TAG, "   Is Streaming: ${rtmpDisplay.isStreaming}")
        Log.i(TAG, "   Is Recording: ${rtmpDisplay.isRecording}")
        
        // Warning messages
        if (actualFps < targetFps * 0.9) {
            Log.w(TAG, "⚠️  WARNING: FPS below target (%.1f%% of target)".format((actualFps / targetFps) * 100))
        }
        if (droppedInPeriod > frameTimeList.size * 0.05) {
            Log.w(TAG, "⚠️  WARNING: High frame drop rate detected")
        }
        if (maxFrameInterval > expectedInterval * 5) {
            Log.w(TAG, "⚠️  WARNING: Large frame interval spike detected ($maxFrameInterval ms)")
        }
        if (usedMemoryMB.toFloat() / maxMemoryMB > 0.8) {
            Log.w(TAG, "⚠️  WARNING: High memory usage")
        }
        
        Log.i(TAG, "═══════════════════════════════════════════════════════")
        
        // Reset counters for next period
        frameCount = 0
        lastStatsTime = currentTime
    }
}
