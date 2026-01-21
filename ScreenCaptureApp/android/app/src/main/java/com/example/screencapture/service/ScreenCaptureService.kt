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
import android.util.DisplayMetrics
import android.view.Gravity
import android.view.View
import android.view.MotionEvent
import android.view.LayoutInflater
import android.graphics.PixelFormat
import android.graphics.Color
import android.graphics.drawable.GradientDrawable
import android.view.ViewGroup
import android.widget.FrameLayout
import android.widget.ImageView
import android.widget.Button
import android.widget.Spinner
import android.widget.ArrayAdapter
import android.widget.RadioGroup
import android.widget.RadioButton
import androidx.appcompat.widget.SwitchCompat
import android.app.AlertDialog
import android.view.ContextThemeWrapper
import android.view.WindowManager
import android.util.Log
import android.widget.Toast
import androidx.core.app.NotificationCompat
import android.os.Looper
import kotlin.math.abs
import com.example.screencapture.R
import com.pedro.common.ConnectChecker
import com.pedro.library.rtmp.RtmpDisplay

class ScreenCaptureService : Service(), ConnectChecker {

    companion object {
        private const val TAG = "ScreenCaptureService"
        private const val NOTIFICATION_ID = 1001
        private const val CHANNEL_ID = "screen_capture_channel"
        
        // 브로드캐스트 액션
        const val ACTION_CONNECTION_STATUS = "com.example.screencapture.CONNECTION_STATUS"
        const val ACTION_UPDATE_SETTINGS = "com.example.screencapture.UPDATE_SETTINGS" // New Action
        const val EXTRA_STATUS = "status"
        const val EXTRA_MESSAGE = "message"
        const val EXTRA_URL = "url"
        const val EXTRA_BITRATE = "bitrate" // New Extra
        const val EXTRA_FPS = "fps"         // New Extra
        const val EXTRA_RESOLUTION_INDEX = "resolution_index" // New Extra
        const val EXTRA_USE_NATIVE_RES = "use_native_res" // New Extra
        
        // 상태 코드
        const val STATUS_STARTING = "starting"
        const val STATUS_CONNECTING = "connecting"
        const val STATUS_CONNECTED = "connected"
        const val STATUS_FAILED = "failed"
        const val STATUS_DISCONNECTED = "disconnected"
    }

    private lateinit var rtmpDisplay: RtmpDisplay
    private var screenWidth = 0
    private var screenHeight = 0
    private var screenDensity = 0
    private var rtmpUrl = ""
    private var isStreaming = false
    
    // Performance monitoring
    private var frameCount = 0
    private var droppedFrames = 0
    private var lastFrameTime = 0L
    private var lastStatsTime = 0L
    private var totalEncodingTime = 0L
    private var encodingCount = 0
    private val frameTimeList = mutableListOf<Long>()
    private val performanceHandler = android.os.Handler(android.os.Looper.getMainLooper())
    
    // MediaProjection 정보 저장 (해상도 변경 시 재사용)
    private var savedResultCode: Int = -1
    private var savedData: Intent? = null

    // Floating Control Ball
    private var floatingControlView: View? = null
    private var windowManager: WindowManager? = null
    private var floatingLayoutParams: WindowManager.LayoutParams? = null
    
    // Reconnection logic
    private var isIntentionalStop = false
    private var retryCount = 0
    private val maxRetryDelay = 30000L // Max delay 30 seconds
    private val reconnectHandler = android.os.Handler(android.os.Looper.getMainLooper())
    private val reconnectRunnable = Runnable {
        if (isStreaming && !isIntentionalStop) {
            Log.d(TAG, "🔄 Executing reconnection attempt #$retryCount")
            if (!rtmpDisplay.isStreaming) {
                rtmpDisplay.startStream(rtmpUrl)
            }
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

    private fun startStream(resultCode: Int, data: Intent) {
        if (isStreaming) {
            Log.w(TAG, "Already streaming")
            return
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
            
            // 키프레임 간격 설정 (초 단위)
            // 짧은 간격(1초)으로 설정하면 화면 변화가 적을 때도 계속 전송됨
            val iFrameInterval = 1 // 1초마다 키프레임 생성
            
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
                iFrameInterval  // screenDensity 대신 키프레임 간격 사용
            )
            
            if (!audioReady || !videoReady) {
                Log.e(TAG, "Failed to prepare audio or video")
                updateNotification("준비 실패")
                return
            }
            
            // MediaProjection 설정
            rtmpDisplay.setIntentResult(resultCode, data)
            
            // RTMP 스트리밍 시작
            Log.i(TAG, "📡 Starting stream to: $rtmpUrl")
            sendStatusBroadcast(STATUS_STARTING, "스트리밍 준비 완료. 서버 연결 중...", rtmpUrl)
            
            isIntentionalStop = false // Reset intentional stop flag
            retryCount = 0            // Reset retry counter
            
            rtmpDisplay.startStream(rtmpUrl)
            isStreaming = true
            
            // Start performance monitoring
            startPerformanceMonitoring()
            
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
    }

    override fun onConnectionFailed(reason: String) {
        Log.e(TAG, "❌ Connection failed: $reason")
        
        if (isIntentionalStop) {
            Log.d(TAG, "Connection failed but it was intentional stop. Ignoring.")
            return
        }

        // Smart Reconnect Logic
        retryCount++
        val delay = calculateRetryDelay(retryCount)
        
        updateNotification("연결 실패. ${delay/1000}초 후 재시도 (${retryCount}회)")
        sendStatusBroadcast(STATUS_CONNECTING, "서버 연결 실패. ${delay/1000}초 후 재시도 중... (${retryCount}회)")
        
        Log.w(TAG, "🔄 Scheduling reconnect attempt #$retryCount in ${delay}ms")
        reconnectHandler.postDelayed(reconnectRunnable, delay)
    }
    
    private fun calculateRetryDelay(attempt: Int): Long {
        // Exponential backoff: 3s, 6s, 12s, 24s, 30s(max)...
        var delay = 3000L * (1L shl (attempt - 1))
        if (delay > maxRetryDelay) delay = maxRetryDelay
        return delay
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
        Log.d(TAG, "🔌 Disconnected")
        
        if (isIntentionalStop) {
            updateNotification("연결 끊김")
            sendStatusBroadcast(STATUS_DISCONNECTED, "서버와 연결이 끊어졌습니다")
        } else {
            // Unexpected disconnect - treat as failure and retry
            Log.w(TAG, "⚠️ Unexpected disconnect! Attempting to reconnect...")
            onConnectionFailed("Connection lost unexpectedly")
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

            // Create Floating Ball View
            val ballView = ImageView(this).apply {
                setImageResource(R.drawable.ic_launcher) // Use app icon or custom drawable
                background = GradientDrawable().apply {
                    shape = GradientDrawable.OVAL
                    setColor(Color.parseColor("#CCFFFFFF")) // Semi-transparent white
                    setStroke(2, Color.GRAY)
                }
                setPadding(20, 20, 20, 20)
                elevation = 10f
            }
            
            // Layout params for the ImageView size
            val size = (60 * resources.displayMetrics.density).toInt()
            val layoutParams = ViewGroup.LayoutParams(size, size)
            ballView.layoutParams = layoutParams

            // Touch Listener for Drag & Click
            ballView.setOnTouchListener(object : View.OnTouchListener {
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
                            
                            // 10픽셀 이상 움직이면 클릭이 아님 (드래그로 간주)
                            if (abs(dx) > 10 || abs(dy) > 10) {
                                isClick = false
                            }

                            floatingLayoutParams!!.x = initialX + dx
                            floatingLayoutParams!!.y = initialY + dy
                            windowManager?.updateViewLayout(floatingControlView, floatingLayoutParams)
                            return true
                        }
                        MotionEvent.ACTION_UP -> {
                            if (isClick) {
                                showOverlaySettingsDialog()
                            }
                            return true
                        }
                    }
                    return false
                }
            })

            floatingControlView = ballView
            windowManager?.addView(floatingControlView, floatingLayoutParams)
            
        } catch (e: Exception) {
            Log.e(TAG, "Error showing floating control: ${e.message}", e)
        }
    }

    private fun removeFloatingControl() {
        if (floatingControlView != null) {
            try {
                windowManager?.removeView(floatingControlView)
                floatingControlView = null
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
