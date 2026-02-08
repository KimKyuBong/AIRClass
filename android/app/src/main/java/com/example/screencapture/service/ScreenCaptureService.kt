package com.example.screencapture.service

import android.app.Activity
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import android.os.Looper
import android.util.DisplayMetrics
import android.util.Log
import android.view.Gravity
import android.view.View
import android.view.MotionEvent
import android.view.LayoutInflater
import android.graphics.PixelFormat
import android.graphics.Color
import android.graphics.drawable.GradientDrawable
import android.view.ViewGroup
import android.view.WindowManager
import android.view.OrientationEventListener
import android.widget.FrameLayout
import android.widget.ImageView
import android.widget.Button
import android.widget.Spinner
import android.widget.ArrayAdapter
import android.widget.RadioGroup
import android.widget.RadioButton
import android.widget.Toast
import android.widget.TextView
import androidx.appcompat.widget.SwitchCompat
import android.app.AlertDialog
import android.view.ContextThemeWrapper
import androidx.core.app.NotificationCompat
import kotlin.math.abs
import com.example.screencapture.R
import io.livekit.android.ConnectOptions
import io.livekit.android.LiveKit
import io.livekit.android.room.Room
import io.livekit.android.room.track.screencapture.ScreenCaptureParams
import io.livekit.android.events.RoomEvent
import io.livekit.android.events.collect
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

import android.animation.ObjectAnimator
import android.animation.ValueAnimator
import android.view.animation.AccelerateDecelerateInterpolator
import android.graphics.PointF
import kotlin.math.cos
import kotlin.math.sin
import java.net.HttpURLConnection
import java.net.URL
import org.json.JSONObject

class ScreenCaptureService : Service() {

    companion object {
        private const val TAG = "ScreenCaptureService"
        private const val NOTIFICATION_ID = 1001
        private const val CHANNEL_ID = "screen_capture_channel"
        
        // 브로드캐스트 액션
        const val ACTION_CONNECTION_STATUS = "com.example.screencapture.CONNECTION_STATUS"
        const val ACTION_UPDATE_SETTINGS = "com.example.screencapture.UPDATE_SETTINGS"
        const val EXTRA_STATUS = "status"
        const val EXTRA_MESSAGE = "message"
        const val EXTRA_URL = "url"
        const val EXTRA_BITRATE = "bitrate"
        const val EXTRA_FPS = "fps"
        const val EXTRA_RESOLUTION_INDEX = "resolution_index"
        const val EXTRA_USE_NATIVE_RES = "use_native_res"
        
        // 상태 코드
        const val STATUS_STARTING = "starting"
        const val STATUS_CONNECTING = "connecting"
        const val STATUS_CONNECTED = "connected"
        const val STATUS_FAILED = "failed"
        const val STATUS_DISCONNECTED = "disconnected"
    }

    private var room: Room? = null
    private val serviceScope = CoroutineScope(Dispatchers.Main + SupervisorJob())
    private var liveKitUrl = ""
    private var screenWidth = 0
    private var screenHeight = 0
    private var screenDensity = 0
    private var isStreaming = false
    
    // MediaProjection 정보 저장 (해상도 변경 시 재사용)
    private var savedResultCode: Int = -1
    private var savedData: Intent? = null

    // Reconnection logic
    private var isIntentionalStop = false
    private var retryCount = 0

    /**
     * 메인 노드에서 LiveKit 토큰 발급 (WebRTC 송출용).
     * serverIp는 "host" 또는 "host:port" 형식.
     */
    private fun fetchLiveKitToken(serverIp: String): Pair<String, String>? {
        Log.d(TAG, "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        Log.d(TAG, "🌐 fetchLiveKitToken() 시작")
        Log.d(TAG, "📥 입력 서버 주소: $serverIp")
        
        val (host, port) = if (serverIp.contains(":")) {
            val parts = serverIp.split(":", limit = 2)
            parts[0] to (parts.getOrNull(1)?.toIntOrNull() ?: 8000)
        } else {
            serverIp to 8000
        }
        Log.d(TAG, "📍 파싱 결과 - host=$host, port=$port")
        
        var conn: HttpURLConnection? = null
        try {
            val url = URL("http://$host:$port/api/livekit/token?user_id=android&room_name=class&user_type=teacher&emulator=true")
            Log.d(TAG, "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            Log.d(TAG, "🔗 HTTP 요청 시작")
            Log.d(TAG, "   방식: GET")
            Log.d(TAG, "   URL: $url")
            Log.d(TAG, "   타임아웃: connect=5000ms, read=5000ms")
            
            conn = url.openConnection() as HttpURLConnection
            conn.requestMethod = "GET"
            conn.connectTimeout = 5000
            conn.readTimeout = 5000
            
            // 로컬 및 원격 주소 로깅
            Log.d(TAG, "⏳ 연결 시도 중...")
            val startTime = System.currentTimeMillis()
            conn.connect()
            val connectTime = System.currentTimeMillis() - startTime
            Log.d(TAG, "✅ TCP 연결 성공 (${connectTime}ms)")
            
            val responseCode = conn.responseCode
            val responseMessage = conn.responseMessage
            Log.d(TAG, "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            Log.d(TAG, "📡 HTTP 응답 수신")
            Log.d(TAG, "   상태 코드: $responseCode")
            Log.d(TAG, "   상태 메시지: $responseMessage")
            Log.d(TAG, "   Content-Type: ${conn.contentType}")
            Log.d(TAG, "   Content-Length: ${conn.contentLength}")
            
            if (responseCode != 200) {
                Log.e(TAG, "❌ HTTP 에러 응답")
                val errorBody = conn.errorStream?.bufferedReader()?.use { it.readText() }
                Log.e(TAG, "   에러 본문: $errorBody")
                return null
            }
            
            val body = conn.inputStream?.bufferedReader()?.use { it.readText() } ?: run {
                Log.e(TAG, "❌ 응답 본문이 비어있음")
                return null
            }
            Log.d(TAG, "📦 응답 본문 길이: ${body.length} bytes")
            Log.d(TAG, "📦 응답 본문 (처음 200자): ${body.take(200)}...")
            
            val json = JSONObject(body)
            Log.d(TAG, "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            Log.d(TAG, "🔍 JSON 파싱 시작")
            
            val token = json.optString("token", "").takeIf { it.isNotBlank() } ?: run {
                Log.e(TAG, "❌ 토큰이 응답에 없음")
                Log.e(TAG, "   JSON 키: ${json.keys().asSequence().toList()}")
                return null
            }
            
            val serverUrl = json.optString("url", "")
            Log.d(TAG, "✅ 토큰 추출 성공")
            Log.d(TAG, "   토큰 길이: ${token.length} chars")
            Log.d(TAG, "   토큰 앞부분: ${token.take(50)}...")
            Log.d(TAG, "   서버 응답 URL: $serverUrl")
            
            // 사용자가 입력한 주소로 LiveKit 연결 (서버 응답 url 무시)
            val wsUrl = "ws://$host:7880"
            Log.d(TAG, "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            Log.d(TAG, "🎯 WebSocket 연결 정보")
            Log.d(TAG, "   사용할 주소: $wsUrl")
            Log.d(TAG, "   (서버 응답 URL은 무시: $serverUrl)")
            Log.d(TAG, "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            
            return token to wsUrl
        } catch (e: java.net.UnknownHostException) {
            Log.e(TAG, "❌ DNS 조회 실패")
            Log.e(TAG, "   호스트: $host")
            Log.e(TAG, "   에러: ${e.message}")
            e.printStackTrace()
            return null
        } catch (e: java.net.ConnectException) {
            Log.e(TAG, "❌ TCP 연결 실패")
            Log.e(TAG, "   대상: $host:$port")
            Log.e(TAG, "   에러: ${e.message}")
            e.printStackTrace()
            return null
        } catch (e: java.net.SocketTimeoutException) {
            Log.e(TAG, "❌ 연결 타임아웃")
            Log.e(TAG, "   대상: $host:$port")
            Log.e(TAG, "   에러: ${e.message}")
            e.printStackTrace()
            return null
        } catch (e: Exception) {
            Log.e(TAG, "❌ 예상치 못한 에러")
            Log.e(TAG, "   타입: ${e.javaClass.simpleName}")
            Log.e(TAG, "   메시지: ${e.message}")
            e.printStackTrace()
            return null
        } finally {
            conn?.disconnect()
            Log.d(TAG, "🔌 HTTP 연결 종료")
            Log.d(TAG, "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        }
    }

    private val reconnectHandler = android.os.Handler(Looper.getMainLooper())
    private val reconnectRunnable = Runnable {
        if (isStreaming && !isIntentionalStop && savedResultCode != -1 && savedData != null) {
            Log.d(TAG, "🔄 Executing reconnection attempt #$retryCount")
            startStream(savedResultCode, savedData!!)
        }
    }

    // Floating Control & Menu
    private var mWindowManager: WindowManager? = null
    private var floatingLayoutParams: WindowManager.LayoutParams? = null
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

    // Keep-Alive Logic: 부드러운 호흡 애니메이션
    private fun startKeepAliveAnimation() {
        stopKeepAliveAnimation()
        
        if (floatingLayout == null) {
            android.os.Handler(Looper.getMainLooper()).postDelayed({
                if (isStreaming) startKeepAliveAnimation()
            }, 1000)
            return
        }

        Log.i(TAG, "✨ Starting breathing animation (Alpha 0.60 <-> 0.65) for static screen support")
        
        breathingAnimator = ObjectAnimator.ofFloat(floatingLayout, "alpha", 0.60f, 0.65f).apply {
            duration = 1000 // 1초
            repeatMode = ValueAnimator.REVERSE
            repeatCount = ValueAnimator.INFINITE
            interpolator = AccelerateDecelerateInterpolator()
            
            addUpdateListener { 
                if (floatingLayout != null && floatingLayoutParams != null) {
                    try {
                        mWindowManager?.updateViewLayout(floatingLayout, floatingLayoutParams)
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
        floatingLayout?.alpha = 0.6f 
        Log.i(TAG, "✨ Breathing animation stopped")
    }

    override fun onCreate() {
        super.onCreate()
        initScreenMetrics()
        createNotificationChannel()
        LiveKit.init(applicationContext)
        Log.d(TAG, "Service created (WebRTC/LiveKit)")
    }

    private fun initScreenMetrics() {
        val windowManager = getSystemService(Context.WINDOW_SERVICE) as WindowManager
        val metrics = DisplayMetrics()
        
        // Service context - use WindowManager
        @Suppress("DEPRECATION")
        windowManager.defaultDisplay.getRealMetrics(metrics)
        
        screenWidth = metrics.widthPixels
        screenHeight = metrics.heightPixels
        screenDensity = metrics.densityDpi
        
        Log.d(TAG, "Screen: ${screenWidth}x${screenHeight}, DPI: $screenDensity")
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_UPDATE_SETTINGS) {
            handleSettingsUpdate(intent)
            return START_STICKY
        }

        val notification = createNotification("대기 중...")
        
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(NOTIFICATION_ID, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PROJECTION)
        } else {
            startForeground(NOTIFICATION_ID, notification)
        }

        Log.d(TAG, "🔍 onStartCommand called")
        
        intent?.let {
            val resultCode = it.getIntExtra("resultCode", -1)
            val data = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                it.getParcelableExtra("data", Intent::class.java)
            } else {
                @Suppress("DEPRECATION")
                it.getParcelableExtra<Intent>("data")
            }
            
            val prefs = getSharedPreferences("settings", Context.MODE_PRIVATE)
            val serverIp = prefs.getString("server_ip", "10.0.2.2") ?: "10.0.2.2"
            
            Log.i(TAG, "🎬 Service Starting - Server: $serverIp (WebRTC)")
            
            if (resultCode != Activity.RESULT_OK || data == null) {
                Log.e(TAG, "❌ Cannot start stream - Invalid data")
                return START_STICKY
            }
            savedResultCode = resultCode
            savedData = data
            startStream(resultCode, data)
        }

        return START_STICKY
    }

    private fun startStream(resultCode: Int, data: Intent, isReconnection: Boolean = false) {
        Log.d(TAG, "▶️ startStream() called - isStreaming=$isStreaming, isReconnection=$isReconnection")
        if (isStreaming) {
            Log.w(TAG, "⚠️ Already streaming, ignoring startStream call")
            return
        }
        
        initScreenMetrics()
        if (!isReconnection) {
            savedResultCode = resultCode
            savedData = data
        }
        
        val prefs = getSharedPreferences("settings", Context.MODE_PRIVATE)
        val serverIp = prefs.getString("server_ip", "10.0.2.2") ?: "10.0.2.2"
        val audioEnabled = getSharedPreferences("streaming_settings", Context.MODE_PRIVATE).getBoolean("audio_enabled", true)
        
        Log.i(TAG, "🎯 서버 설정: IP=$serverIp, audio=$audioEnabled")
        sendStatusBroadcast(STATUS_STARTING, "토큰 발급 중... (서버: $serverIp)", liveKitUrl)
        updateNotification("토큰 발급 중...")
        updateStatusColor(STATUS_CONNECTING)
        isIntentionalStop = false
        retryCount = 0
        
        Log.d(TAG, "🚀 Launching coroutine for token fetch...")
        serviceScope.launch {
            try {
                Log.d(TAG, "🔄 Fetching token from $serverIp...")
                val tokenResult = withContext(Dispatchers.IO) { fetchLiveKitToken(serverIp) }
                if (tokenResult == null) {
                    Log.e(TAG, "❌ LiveKit 토큰 발급 실패")
                    updateNotification("토큰 발급 실패")
                    sendStatusBroadcast(STATUS_FAILED, "서버($serverIp)에서 토큰을 받지 못했습니다.")
                    updateStatusColor(STATUS_FAILED)
                    if (!isIntentionalStop) {
                        retryCount++
                        Log.w(TAG, "🔄 재연결 시도 예약 (attempt #$retryCount)")
                        reconnectHandler.postDelayed(reconnectRunnable, 3000L)
                    }
                    return@launch
                }
                val (token, wsUrl) = tokenResult
                liveKitUrl = wsUrl
                Log.i(TAG, "✅ 토큰 발급 성공!")
                Log.i(TAG, "📡 WebRTC 연결 준비: $wsUrl (room: class)")
                Log.d(TAG, "🔑 Token: ${token.take(30)}...")
                sendStatusBroadcast(STATUS_CONNECTING, "LiveKit 연결 중...", wsUrl)
                updateNotification("LiveKit 연결 중...")
                
                Log.d(TAG, "🏗️ LiveKit 인스턴스 생성 중...")
                val r = LiveKit.create(applicationContext)
                room = r
                Log.d(TAG, "✅ LiveKit 인스턴스 생성 완료")
                
                Log.d(TAG, "📦 ScreenCaptureParams 생성 중...")
                val params = ScreenCaptureParams(mediaProjectionPermissionResultData = data)
                Log.d(TAG, "✅ ScreenCaptureParams 생성 완료")
                
                Log.d(TAG, "🎧 이벤트 리스너 시작...")
                serviceScope.launch {
                    r.events.collect { event ->
                        val eventName = event.javaClass.simpleName
                        Log.d(TAG, "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                        Log.d(TAG, "📥 LiveKit 이벤트 수신: $eventName")
                        Log.d(TAG, "   시각: ${System.currentTimeMillis()}")
                        
                        when (event) {
                            is RoomEvent.Connected -> {
                                Log.i(TAG, "✅ LiveKit 연결 성공!")
                                Log.i(TAG, "   Room State: CONNECTED")
                                retryCount = 0
                                reconnectHandler.removeCallbacks(reconnectRunnable)
                                
                                Log.d(TAG, "🖥️ 화면 공유 활성화 시도...")
                                val enabled = r.localParticipant.setScreenShareEnabled(true, params)
                                if (!enabled) {
                                    Log.e(TAG, "❌ 화면 공유 활성화 실패")
                                    updateNotification("화면 공유 실패")
                                    sendStatusBroadcast(STATUS_FAILED, "화면 공유를 켤 수 없습니다", liveKitUrl)
                                    updateStatusColor(STATUS_FAILED)
                                    r.disconnect()
                                    return@collect
                                }
                                Log.i(TAG, "✅ 화면 공유 활성화 성공!")
                                
                                isStreaming = true
                                startKeepAliveAnimation()
                                startOrientationListener()
                                showFloatingControl()
                                updateNotification("✅ 스트리밍 중 - $liveKitUrl")
                                sendStatusBroadcast(STATUS_CONNECTED, "연결 성공! 스트리밍 중", liveKitUrl)
                                updateStatusColor(STATUS_CONNECTED)
                                startHeartbeat()
                                Log.i(TAG, "🎉 스트리밍 시작 완료!")
                            }
                            is RoomEvent.Disconnected -> {
                                Log.w(TAG, "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                                Log.w(TAG, "⚠️ LiveKit 연결 끊김")
                                Log.w(TAG, "   사유: ${event.reason}")
                                Log.w(TAG, "   의도적 중지: $isIntentionalStop")
                                Log.w(TAG, "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                                isStreaming = false
                                removeFloatingControl()
                                updateStatusColor(STATUS_DISCONNECTED)
                                if (isIntentionalStop) {
                                    updateNotification("연결 끊김 (의도적 중지)")
                                    sendStatusBroadcast(STATUS_DISCONNECTED, "서버와 연결이 끊어졌습니다", liveKitUrl)
                                } else {
                                    retryCount++
                                    Log.w(TAG, "🔄 자동 재연결 시도 예약 (attempt #$retryCount)")
                                    updateNotification("재연결 대기 중... (#$retryCount)")
                                    sendStatusBroadcast(STATUS_CONNECTING, "재연결 대기 중... (#$retryCount)", liveKitUrl)
                                    reconnectHandler.postDelayed(reconnectRunnable, 3000L)
                                }
                                stopHeartbeat()
                            }
                            is RoomEvent.FailedToConnect -> {
                                Log.e(TAG, "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                                Log.e(TAG, "❌ LiveKit 연결 실패")
                                Log.e(TAG, "   에러: ${event.error}")
                                Log.e(TAG, "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                            }
                            else -> {
                                Log.d(TAG, "📋 기타 이벤트: $eventName")
                                if (event is RoomEvent.TrackPublished) {
                                    Log.d(TAG, "   - 트랙 발행됨")
                                } else if (event is RoomEvent.TrackUnpublished) {
                                    Log.d(TAG, "   - 트랙 발행 취소됨")
                                }
                                Log.d(TAG, "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                            }
                        }
                    }
                }
                Log.d(TAG, "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                Log.d(TAG, "🔌 LiveKit WebSocket 연결 시작")
                Log.d(TAG, "   대상 URL: $wsUrl")
                Log.d(TAG, "   토큰 길이: ${token.length} chars")
                Log.d(TAG, "   오디오: $audioEnabled")
                Log.d(TAG, "   비디오: false")
                Log.d(TAG, "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                
                val connectStartTime = System.currentTimeMillis()
                r.connect(
                    wsUrl,
                    token,
                    ConnectOptions(audio = audioEnabled, video = false)
                )
                val connectCallTime = System.currentTimeMillis() - connectStartTime
                
                Log.d(TAG, "✅ r.connect() 호출 완료 (${connectCallTime}ms)")
                Log.d(TAG, "⏳ WebSocket 핸드셰이크 대기 중...")
                Log.d(TAG, "   - Connected 이벤트를 기다립니다")
                Log.d(TAG, "   - 이벤트 리스너가 별도 코루틴에서 실행 중")
                Log.d(TAG, "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                
                updateNotification("WebSocket 연결 중...")
                sendStatusBroadcast(STATUS_CONNECTING, "WebSocket 연결 중...", wsUrl)
                
            } catch (e: Exception) {
                Log.e(TAG, "❌ 스트리밍 시작 실패: ${e.javaClass.simpleName}: ${e.message}", e)
                e.printStackTrace()
                updateNotification("연결 실패: ${e.message}")
                sendStatusBroadcast(STATUS_FAILED, "연결 실패: ${e.message}", liveKitUrl)
                updateStatusColor(STATUS_FAILED)
                room?.disconnect()
                room = null
                if (!isIntentionalStop) {
                    retryCount++
                    Log.w(TAG, "🔄 에러 후 재연결 시도 예약 (attempt #$retryCount)")
                    reconnectHandler.postDelayed(reconnectRunnable, 3000L)
                }
            }
        }
    }

    // Orientation handling
    private var orientationEventListener: OrientationEventListener? = null
    private var lastOrientation = -1
    
    private fun startOrientationListener() {
        if (orientationEventListener == null) {
            orientationEventListener = object : OrientationEventListener(this) {
                override fun onOrientationChanged(orientation: Int) {
                    if (orientation == ORIENTATION_UNKNOWN) return
                    
                    // Convert to 0, 90, 180, 270 (with some tolerance)
                    val newOrientation = when {
                        orientation >= 340 || orientation < 20 -> 0   // Portrait
                        orientation in 70..110 -> 90                  // Landscape
                        orientation in 160..200 -> 180                // Reverse Portrait
                        orientation in 250..290 -> 270                // Reverse Landscape
                        else -> return // Ignore intermediate angles
                    }
                    
                    if (lastOrientation != -1 && lastOrientation != newOrientation) {
                        // Orientation changed (e.g. Portrait <-> Landscape)
                        val isPortraitToLandscape = (lastOrientation == 0 || lastOrientation == 180) && (newOrientation == 90 || newOrientation == 270)
                        val isLandscapeToPortrait = (lastOrientation == 90 || lastOrientation == 270) && (newOrientation == 0 || newOrientation == 180)
                        
                        if (isPortraitToLandscape || isLandscapeToPortrait) {
                            Log.i(TAG, "🔄 Orientation changed: $lastOrientation -> $newOrientation. Restarting stream...")
                            
                            // Debounce restart (wait for rotation to settle)
                            stopOrientationListener() // Prevent multiple triggers
                            
                            android.os.Handler(Looper.getMainLooper()).postDelayed({
                                restartStreamWithNewSettings()
                            }, 1000) // 1 second delay for UI to settle
                        }
                    }
                    lastOrientation = newOrientation
                }
            }
        }
        
        if (orientationEventListener?.canDetectOrientation() == true) {
            orientationEventListener?.enable()
            Log.i(TAG, "🔄 Orientation listener started")
        }
    }
    
    private fun stopOrientationListener() {
        orientationEventListener?.disable()
        Log.i(TAG, "🔄 Orientation listener stopped")
    }

    private fun stopStream() {
        if (!isStreaming) return
        
        isIntentionalStop = true
        reconnectHandler.removeCallbacks(reconnectRunnable)
        stopHeartbeat()
        stopKeepAliveAnimation()
        stopOrientationListener()
        
        try {
            removeFloatingControl()
            val r = room
            room = null
            isStreaming = false
            serviceScope.launch {
                try {
                    r?.localParticipant?.setScreenShareEnabled(false)
                } catch (_: Exception) { }
                r?.disconnect()
                r?.release()
            }
            updateNotification("스트리밍 중지됨")
            Log.i(TAG, "Streaming stopped (WebRTC)")
        } catch (e: Exception) {
            Log.e(TAG, "Error stopping stream: ${e.message}", e)
        }
    }
    
    private fun restartStreamWithNewSettings() {
        try {
            if (savedResultCode == -1 || savedData == null) {
                Toast.makeText(this, "재시작 실패: 화면 캡처 정보가 없습니다", Toast.LENGTH_SHORT).show()
                return
            }
            
            if (isStreaming) stopStream()
            
            android.os.Handler(Looper.getMainLooper()).postDelayed({
                try {
                    startStream(savedResultCode, savedData!!)
                } catch (e: Exception) {
                    Toast.makeText(this, "재시작 실패: ${e.message}", Toast.LENGTH_SHORT).show()
                }
            }, 500)
            
        } catch (e: Exception) {
            Log.e(TAG, "❌ Error in restartStreamWithNewSettings: ${e.message}", e)
        }
    }

    private fun handleSettingsUpdate(intent: Intent) {
        if (!isStreaming) return
        
        val newBitrateIndex = intent.getIntExtra(EXTRA_BITRATE, -1)
        val newFpsIndex = intent.getIntExtra(EXTRA_FPS, -1)
        val newResIndex = intent.getIntExtra(EXTRA_RESOLUTION_INDEX, -1)
        val newUseNative = intent.getBooleanExtra(EXTRA_USE_NATIVE_RES, false)
        
        val prefs = getSharedPreferences("streaming_settings", Context.MODE_PRIVATE)
        val currentBitrateIndex = prefs.getInt("bitrate", 2)
        val currentFpsIndex = prefs.getInt("fps", 2)
        val currentResIndex = prefs.getInt("resolution", 0)
        val currentUseNative = prefs.getBoolean("use_native_res", false)
        
        if (newBitrateIndex != -1 && newBitrateIndex != currentBitrateIndex) {
            prefs.edit().putInt("bitrate", newBitrateIndex).apply()
            Toast.makeText(this, "비트레이트 설정 저장 (재시작 시 적용)", Toast.LENGTH_SHORT).show()
        }
        
        // Resolution/FPS Change (Restart)
        val resChanged = (newResIndex != -1 && newResIndex != currentResIndex) || (newUseNative != currentUseNative)
        val fpsChanged = (newFpsIndex != -1 && newFpsIndex != currentFpsIndex)
        
        if (resChanged || fpsChanged) {
            prefs.edit().apply {
                if (newResIndex != -1) putInt("resolution", newResIndex)
                if (newFpsIndex != -1) putInt("fps", newFpsIndex)
                putBoolean("use_native_res", newUseNative)
                apply()
            }
            Toast.makeText(this, "해상도 변경을 위해 재시작합니다...", Toast.LENGTH_SHORT).show()
            restartStreamWithNewSettings()
        }
    }
    
    // --- UI & Floating Control ---

    private fun showFloatingControl() {
        removeFloatingControl()

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M && !android.provider.Settings.canDrawOverlays(this)) {
            return
        }

        try {
            mWindowManager = getSystemService(WINDOW_SERVICE) as WindowManager
            
            val type = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
            } else {
                @Suppress("DEPRECATION")
                WindowManager.LayoutParams.TYPE_PHONE
            }

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

            floatingLayout = FrameLayout(this).apply {
                // Disable hardware acceleration to fix black screen issue
                setLayerType(View.LAYER_TYPE_SOFTWARE, null)
            }
            
            menuContainer = FrameLayout(this).apply {
                visibility = View.GONE
            }
            floatingLayout?.addView(menuContainer, FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
            ))

            val ballSize = (60 * resources.displayMetrics.density).toInt()
            mainBall = ImageView(this).apply {
                setImageResource(R.drawable.ic_launcher)
                background = createStatusBackground(COLOR_WARNING)
                setPadding(15, 15, 15, 15)
                elevation = 10f
                alpha = 0.6f
                // Disable hardware acceleration to fix black screen issue
                setLayerType(View.LAYER_TYPE_SOFTWARE, null)
            }
            
            floatingLayout?.addView(mainBall, FrameLayout.LayoutParams(ballSize, ballSize))

            createMenuItem("설정", 1, ballSize) { showOverlaySettingsDialog() }
            createMenuItem("중지", 2, ballSize) { stopStream() }
            createMenuItem("닫기", 3, ballSize) { toggleMenu(false) }

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
                                if (isMenuExpanded) toggleMenu(false)
                            }
                            floatingLayoutParams!!.x = initialX + dx
                            floatingLayoutParams!!.y = initialY + dy
                            mWindowManager?.updateViewLayout(floatingLayout, floatingLayoutParams)
                            return true
                        }
                        MotionEvent.ACTION_UP -> {
                            if (isClick) toggleMenu(!isMenuExpanded)
                            return true
                        }
                    }
                    return false
                }
            })

            mWindowManager?.addView(floatingLayout, floatingLayoutParams)
            
        } catch (e: Exception) {
            Log.e(TAG, "Error showing floating control: ${e.message}", e)
        }
    }

    private fun createStatusBackground(strokeColor: Int): GradientDrawable {
        return GradientDrawable().apply {
            shape = GradientDrawable.OVAL
            setColor(Color.parseColor("#44000000"))
            setStroke(8, strokeColor)
        }
    }

    private fun createMenuItem(label: String, index: Int, ballSize: Int, onClick: () -> Unit) {
        val btnSize = (50 * resources.displayMetrics.density).toInt()
        val btn = TextView(this).apply {
            text = label
            setTextColor(Color.WHITE)
            gravity = Gravity.CENTER
            textSize = 12f
            background = GradientDrawable().apply {
                shape = GradientDrawable.OVAL
                setColor(Color.parseColor("#99000000"))
                setStroke(2, Color.WHITE)
            }
            setOnClickListener { 
                onClick()
                toggleMenu(false)
            }
        }

        val params = FrameLayout.LayoutParams(btnSize, btnSize)
        val distance = ballSize.toFloat() * 1.2f
        val angle = when(index) {
            1 -> 0.0    // Right
            2 -> 45.0   // Bottom-Right
            else -> 90.0 // Bottom
        }
        val rad = Math.toRadians(angle)
        
        btn.translationX = 0f
        btn.translationY = 0f
        btn.alpha = 0f
        btn.tag = PointF((cos(rad) * distance).toFloat(), (sin(rad) * distance).toFloat())
        
        menuContainer?.addView(btn, params)
    }
    
    private fun toggleMenu(expand: Boolean) {
        isMenuExpanded = expand
        val container = menuContainer ?: return
        
        if (expand) {
            container.visibility = View.VISIBLE
            
            // 윈도우 레이아웃 갱신 (크기 확장)
            // 메뉴가 펼쳐질 공간 확보를 위해 윈도우 크기를 강제로 늘림
            // 애니메이션은 translation을 쓰지만 레이아웃 bounds는 변하지 않기 때문에 필수
            try {
                val expandedSize = (250 * resources.displayMetrics.density).toInt()
                floatingLayoutParams?.width = expandedSize
                floatingLayoutParams?.height = expandedSize
                mWindowManager?.updateViewLayout(floatingLayout, floatingLayoutParams)
                Log.d(TAG, "🎯 Menu expanded - Window size: ${floatingLayoutParams?.width}x${floatingLayoutParams?.height}")
            } catch (e: Exception) {
                Log.e(TAG, "❌ Failed to expand window: ${e.message}")
            }

            for (i in 0 until container.childCount) {
                val child = container.getChildAt(i)
                val target = child.tag as PointF
                Log.d(TAG, "🎯 Menu item $i -> target: (${target.x}, ${target.y})")
                child.animate()
                    .translationX(target.x)
                    .translationY(target.y)
                    .alpha(1f)
                    .setDuration(200)
                    .start()
            }
        } else {
            for (i in 0 until container.childCount) {
                val child = container.getChildAt(i)
                child.animate()
                    .translationX(0f)
                    .translationY(0f)
                    .alpha(0f)
                    .setDuration(200)
                    .withEndAction { 
                        if (i == container.childCount - 1) {
                            container.visibility = View.GONE
                            // 윈도우 레이아웃 갱신 (크기 축소 - 메인 볼 크기로 복귀)
                            try {
                                floatingLayoutParams?.width = WindowManager.LayoutParams.WRAP_CONTENT
                                floatingLayoutParams?.height = WindowManager.LayoutParams.WRAP_CONTENT
                                mWindowManager?.updateViewLayout(floatingLayout, floatingLayoutParams)
                            } catch (e: Exception) {}
                        }
                    }.start()
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
                mWindowManager?.removeView(floatingLayout)
                floatingLayout = null
                mainBall = null
                menuContainer = null
            } catch (e: Exception) { }
        }
    }
    
    private fun showOverlaySettingsDialog() {
        val contextThemeWrapper = ContextThemeWrapper(this, androidx.appcompat.R.style.Theme_AppCompat_Light_Dialog)
        val dialogView = LayoutInflater.from(contextThemeWrapper).inflate(R.layout.dialog_streaming_options, null)

        val rgAspectRatio = dialogView.findViewById<RadioGroup>(R.id.rg_aspect_ratio)
        val rbAspect16_9 = dialogView.findViewById<RadioButton>(R.id.rb_aspect_16_9)
        val rbAspectDevice = dialogView.findViewById<RadioButton>(R.id.rb_aspect_device)
        val resolutionSpinner = dialogView.findViewById<Spinner>(R.id.spinner_resolution)
        val fpsSpinner = dialogView.findViewById<Spinner>(R.id.fpsSpinner)
        val bitrateSpinner = dialogView.findViewById<Spinner>(R.id.bitrateSpinner)
        val audioSwitch = dialogView.findViewById<SwitchCompat>(R.id.audioSwitch)
        
        val resolutions = arrayOf("FHD (1920x1080)", "QHD (2560x1440)", "4K (3840x2160)")
        resolutionSpinner.adapter = ArrayAdapter(contextThemeWrapper, android.R.layout.simple_spinner_dropdown_item, resolutions)
        
        val fpsOptions = arrayOf("15 fps", "24 fps", "30 fps", "60 fps")
        fpsSpinner.adapter = ArrayAdapter(contextThemeWrapper, android.R.layout.simple_spinner_dropdown_item, fpsOptions)
        
        val bitrateOptions = arrayOf("5.0 Mbps", "8.0 Mbps", "10.0 Mbps", "15.0 Mbps", "20.0 Mbps", "25.0 Mbps", "30.0 Mbps")
        bitrateSpinner.adapter = ArrayAdapter(contextThemeWrapper, android.R.layout.simple_spinner_dropdown_item, bitrateOptions)
        
        val prefs = getSharedPreferences("streaming_settings", Context.MODE_PRIVATE)
        val useNativeRes = prefs.getBoolean("use_native_res", false)
        
        if (useNativeRes) {
            rbAspectDevice.isChecked = true
            resolutionSpinner.isEnabled = false
        } else {
            rbAspect16_9.isChecked = true
            resolutionSpinner.isEnabled = true
        }
        
        rgAspectRatio.setOnCheckedChangeListener { _, checkedId ->
            resolutionSpinner.isEnabled = checkedId != R.id.rb_aspect_device
        }
        
        resolutionSpinner.setSelection(prefs.getInt("resolution", 0))
        fpsSpinner.setSelection(prefs.getInt("fps", 2))
        bitrateSpinner.setSelection(prefs.getInt("bitrate", 1))
        audioSwitch.isChecked = prefs.getBoolean("audio_enabled", true)
        
        val dialog = AlertDialog.Builder(contextThemeWrapper).setView(dialogView).create()
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            dialog.window?.setType(WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY)
        } else {
            @Suppress("DEPRECATION")
            dialog.window?.setType(WindowManager.LayoutParams.TYPE_PHONE)
        }
        
        dialogView.findViewById<Button>(R.id.saveButton).setOnClickListener {
            handleInternalSettingsUpdate(
                rbAspectDevice.isChecked,
                resolutionSpinner.selectedItemPosition,
                fpsSpinner.selectedItemPosition,
                bitrateSpinner.selectedItemPosition
            )
            prefs.edit().apply {
                putBoolean("use_native_res", rbAspectDevice.isChecked)
                putInt("resolution", resolutionSpinner.selectedItemPosition)
                putInt("fps", fpsSpinner.selectedItemPosition)
                putInt("bitrate", bitrateSpinner.selectedItemPosition)
                putBoolean("audio_enabled", audioSwitch.isChecked)
                apply()
            }
            Toast.makeText(this, "설정이 변경되었습니다", Toast.LENGTH_SHORT).show()
            dialog.dismiss()
        }
        
        dialogView.findViewById<Button>(R.id.cancelButton).setOnClickListener { dialog.dismiss() }
        dialog.show()
    }
    
    private fun handleInternalSettingsUpdate(newUseNative: Boolean, newResIndex: Int, newFpsIndex: Int, newBitrateIndex: Int) {
        val prefs = getSharedPreferences("streaming_settings", Context.MODE_PRIVATE)
        val currentBitrateIndex = prefs.getInt("bitrate", 2)
        val currentFpsIndex = prefs.getInt("fps", 2)
        val currentResIndex = prefs.getInt("resolution", 0)
        val currentUseNative = prefs.getBoolean("use_native_res", false)
        
        if ((newResIndex != currentResIndex) || (newUseNative != currentUseNative) || (newFpsIndex != currentFpsIndex)) {
            Toast.makeText(this, "설정 적용을 위해 재시작합니다...", Toast.LENGTH_SHORT).show()
            prefs.edit().apply {
                putBoolean("use_native_res", newUseNative)
                putInt("resolution", newResIndex)
                putInt("fps", newFpsIndex)
                apply()
            }
            restartStreamWithNewSettings()
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
        stopHeartbeat()
        removeFloatingControl()
        super.onDestroy()
        Log.d(TAG, "Service destroyed")
    }

    override fun onBind(intent: Intent?): IBinder? = null

    // Heartbeat logic
    private val heartbeatHandler = android.os.Handler(Looper.getMainLooper())
    private val heartbeatRunnable = object : Runnable {
        override fun run() {
            if (isStreaming && !isIntentionalStop) {
                checkServerHealth()
                heartbeatHandler.postDelayed(this, 3000)
            }
        }
    }
    
    private fun startHeartbeat() {
        stopHeartbeat()
        heartbeatHandler.postDelayed(heartbeatRunnable, 3000)
    }
    
    private fun stopHeartbeat() {
        heartbeatHandler.removeCallbacks(heartbeatRunnable)
    }
    
    private fun checkServerHealth() {
        Thread {
            try {
                val prefs = getSharedPreferences("settings", Context.MODE_PRIVATE)
                val serverIp = prefs.getString("server_ip", "10.0.2.2") ?: "10.0.2.2"
                val url = java.net.URL("http://$serverIp:8000/health")
                val connection = url.openConnection() as java.net.HttpURLConnection
                connection.connectTimeout = 2000
                connection.readTimeout = 2000
                connection.requestMethod = "GET"
                
                if (connection.responseCode == 200) {
                    connection.disconnect()
                } else {
                    connection.disconnect()
                }
            } catch (e: Exception) { }
        }.start()
    }

    private fun sendStatusBroadcast(status: String, message: String, url: String = liveKitUrl) {
        val intent = Intent(ACTION_CONNECTION_STATUS).apply {
            putExtra(EXTRA_STATUS, status)
            putExtra(EXTRA_MESSAGE, message)
            putExtra(EXTRA_URL, url)
        }
        sendBroadcast(intent)
    }
    
}