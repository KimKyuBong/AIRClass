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
import com.pedro.common.ConnectChecker
import com.pedro.library.rtmp.RtmpDisplay

import android.animation.ObjectAnimator
import android.animation.ValueAnimator
import android.view.animation.AccelerateDecelerateInterpolator
import android.graphics.PointF
import kotlin.math.cos
import kotlin.math.sin

class ScreenCaptureService : Service(), ConnectChecker {

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
    private val performanceHandler = android.os.Handler(Looper.getMainLooper())
    
    // MediaProjection 정보 저장 (해상도 변경 시 재사용)
    private var savedResultCode: Int = -1
    private var savedData: Intent? = null

    // Reconnection logic
    private var isIntentionalStop = false
    private var retryCount = 0
    private val maxRetryDelay = 30000L // Max delay 30 seconds
    private val reconnectHandler = android.os.Handler(Looper.getMainLooper())
    private val reconnectRunnable = Runnable {
        if (isStreaming && !isIntentionalStop) {
            Log.d(TAG, "🔄 Executing reconnection attempt #$retryCount")
            if (!rtmpDisplay.isStreaming) {
                rtmpDisplay.startStream(rtmpUrl)
            }
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
        
        rtmpDisplay = RtmpDisplay(baseContext, true, this)
        rtmpDisplay.getStreamClient().setReTries(999) 
        
        Log.d(TAG, "Service created")
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
            val serverIp = prefs.getString("server_ip", "192.168.0.12") ?: "192.168.0.12"
            val nodePassword = prefs.getString("node_password", "test") ?: "test"
            
            // RTMP URL에 암호 추가
            rtmpUrl = "rtmp://$serverIp:1935/live/stream?pwd=$nodePassword"
            
            Log.i(TAG, "🎬 Service Starting - Server IP: $serverIp")
            
            if (resultCode == Activity.RESULT_OK && data != null) {
                savedResultCode = resultCode
                savedData = data
                startStream(resultCode, data)
            } else {
                Log.e(TAG, "❌ Cannot start stream - Invalid data")
            }
        }

        return START_STICKY
    }

    private fun startStream(resultCode: Int, data: Intent, isReconnection: Boolean = false) {
        if (isStreaming) return
        
        // 1. 시작하는 순간의 화면 상태(가로/세로)를 최신으로 갱신
        initScreenMetrics()
        
        if (!isReconnection) {
            savedResultCode = resultCode
            savedData = data
        }
        
        try {
            val streamingPrefs = getSharedPreferences("streaming_settings", Context.MODE_PRIVATE)
            val useNativeRes = streamingPrefs.getBoolean("use_native_res", false)
            
            // 2. 현재 기기 방향 확인
            val isPortrait = screenWidth < screenHeight
            
            val (width, height) = if (useNativeRes) {
                val nativeWidth = (screenWidth / 2) * 2
                val nativeHeight = (screenHeight / 2) * 2
                Pair(nativeWidth, nativeHeight)
            } else {
                val resolutionIndex = streamingPrefs.getInt("resolution", 0)
                // 기본값은 가로(Landscape) 기준
                val (baseW, baseH) = when (resolutionIndex) {
                    0 -> Pair(1920, 1080)
                    1 -> Pair(2560, 1440)
                    2 -> Pair(3840, 2160)
                    else -> Pair(1920, 1080)
                }
                
                // 현재 기기 방향에 맞춰 가로/세로 자동 스왑 (자유로운 변환)
                if (isPortrait) {
                    // 세로 모드: 너비 < 높이
                    Pair(kotlin.math.min(baseW, baseH), kotlin.math.max(baseW, baseH))
                } else {
                    // 가로 모드: 너비 > 높이
                    Pair(kotlin.math.max(baseW, baseH), kotlin.math.min(baseW, baseH))
                }
            }
            
            val fpsIndex = streamingPrefs.getInt("fps", 2)
            val fps = when (fpsIndex) {
                0 -> 15; 1 -> 24; 2 -> 30; 3 -> 60; else -> 30
            }
            
            val bitrateIndex = streamingPrefs.getInt("bitrate", 2)
            val bitrate = when (bitrateIndex) {
                0 -> 5000 * 1024; 1 -> 8000 * 1024; 2 -> 10000 * 1024; 3 -> 15000 * 1024
                4 -> 20000 * 1024; 5 -> 25000 * 1024; 6 -> 30000 * 1024; else -> 10000 * 1024
            }
            
            val audioEnabled = streamingPrefs.getBoolean("audio_enabled", true)
            val iFrameInterval = 1 
            
            val audioReady = if (audioEnabled) rtmpDisplay.prepareAudio() else true
            
            // 계산된 최종 해상도로 인코더 준비
            val videoReady = rtmpDisplay.prepareVideo(
                width, height, fps, bitrate, 0, iFrameInterval
            )
            
            if (!audioReady || !videoReady) {
                Log.e(TAG, "Failed to prepare audio or video")
                updateNotification("준비 실패")
                return
            }
            
            rtmpDisplay.setIntentResult(resultCode, data)
            
            Log.i(TAG, "📡 Starting stream to: $rtmpUrl ($width x $height, ${if(isPortrait) "Portrait" else "Landscape"})")
            sendStatusBroadcast(STATUS_STARTING, "스트리밍 준비 완료. 서버 연결 중...", rtmpUrl)
            
            isIntentionalStop = false 
            retryCount = 0            
            
            rtmpDisplay.startStream(rtmpUrl)
            isStreaming = true
            
            startPerformanceMonitoring()
            startHeartbeat()
            startKeepAliveAnimation() // CRITICAL for static screens
            startOrientationListener() // 화면 회전 감지 시작
            showFloatingControl()
            
            updateNotification("스트리밍 중...")
            
        } catch (e: Exception) {
            Log.e(TAG, "❌ Error starting stream: ${e.message}", e)
            updateNotification("시작 실패")
            sendStatusBroadcast(STATUS_FAILED, "스트리밍 시작 실패: ${e.message}")
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
        stopOrientationListener() // Stop orientation listener
        
        try {
            stopPerformanceMonitoring()
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
    
    private fun restartStreamWithNewSettings() {
        try {
            if (savedResultCode == -1 || savedData == null) {
                Toast.makeText(this, "재시작 실패: 화면 캡처 정보가 없습니다", Toast.LENGTH_SHORT).show()
                return
            }
            
            if (isStreaming) {
                try {
                    if (rtmpDisplay.isStreaming) rtmpDisplay.stopStream()
                    isStreaming = false
                } catch (e: Exception) { }
            }
            
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
        
        // Bitrate Change (Real-time)
        if (newBitrateIndex != -1 && newBitrateIndex != currentBitrateIndex) {
            val bitrate = when (newBitrateIndex) {
                0 -> 5000 * 1024; 1 -> 8000 * 1024; 2 -> 10000 * 1024; 3 -> 15000 * 1024
                4 -> 20000 * 1024; 5 -> 25000 * 1024; 6 -> 30000 * 1024; else -> 10000 * 1024
            }
            try {
                rtmpDisplay.setVideoBitrateOnFly(bitrate)
                prefs.edit().putInt("bitrate", newBitrateIndex).apply()
                Toast.makeText(this, "비트레이트 변경됨", Toast.LENGTH_SHORT).show()
            } catch (e: Exception) { }
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

            floatingLayout = FrameLayout(this)
            
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
            1 -> -45.0; 2 -> 0.0; else -> 45.0
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
            } catch (e: Exception) {}

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
        
        if (newBitrateIndex != currentBitrateIndex) {
            val bitrate = when (newBitrateIndex) {
                0 -> 5000 * 1024; 1 -> 8000 * 1024; 2 -> 10000 * 1024; 3 -> 15000 * 1024
                4 -> 20000 * 1024; 5 -> 25000 * 1024; 6 -> 30000 * 1024; else -> 10000 * 1024
            }
            try { rtmpDisplay.setVideoBitrateOnFly(bitrate) } catch (e: Exception) { }
        }
        
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
                    val responseBody = connection.inputStream.bufferedReader().use { it.readText() }
                    connection.disconnect()
                    
                    try {
                        val json = org.json.JSONObject(responseBody)
                        if (!json.optBoolean("stream_active", false) && rtmpDisplay.isStreaming) {
                            android.os.Handler(Looper.getMainLooper()).post {
                                if (!isIntentionalStop) {
                                    retryCount++
                                    updateNotification("서버 재연결 중...")
                                    try { rtmpDisplay.getStreamClient().reTry(2000L, "Stream inactive", rtmpUrl) } catch (e: Exception) {}
                                }
                            }
                        }
                    } catch (e: Exception) { }
                } else {
                    connection.disconnect()
                }
            } catch (e: Exception) { }
        }.start()
    }

    // ConnectChecker Implementation
    override fun onConnectionStarted(url: String) {
        updateNotification("연결 중...")
        sendStatusBroadcast(STATUS_CONNECTING, "서버에 연결 중...", url)
        updateStatusColor(STATUS_CONNECTING)
    }

    override fun onConnectionSuccess() {
        retryCount = 0 
        reconnectHandler.removeCallbacks(reconnectRunnable)
        updateNotification("연결 성공 - 스트리밍 중")
        sendStatusBroadcast(STATUS_CONNECTED, "연결 성공! 스트리밍 중")
        updateStatusColor(STATUS_CONNECTED)
        startHeartbeat()
    }

    override fun onConnectionFailed(reason: String) {
        updateStatusColor(STATUS_FAILED)
        if (isIntentionalStop) return

        retryCount++
        val delay = if (retryCount <= 2) 2000L else 5000L
        updateNotification("연결 실패. 재시도 중...")
        sendStatusBroadcast(STATUS_CONNECTING, "서버 연결 실패. 재시도 중...")
        reconnectHandler.postDelayed(reconnectRunnable, delay)
    }

    override fun onDisconnect() {
        updateStatusColor(STATUS_DISCONNECTED)
        if (isIntentionalStop) {
            updateNotification("연결 끊김")
            sendStatusBroadcast(STATUS_DISCONNECTED, "서버와 연결이 끊어졌습니다")
            return
        }
        
        retryCount++
        updateNotification("서버 재연결 대기 중...")
        sendStatusBroadcast(STATUS_CONNECTING, "재연결 대기 중...")
        try { rtmpDisplay.getStreamClient().reTry(3000L, "Disconnect", rtmpUrl) } catch (e: Exception) { stopHeartbeat() }
    }

    override fun onAuthError() {
        updateNotification("인증 오류")
        sendStatusBroadcast(STATUS_FAILED, "서버 인증 오류")
        updateStatusColor(STATUS_FAILED)
    }

    override fun onAuthSuccess() { }
    
    override fun onNewBitrate(bitrate: Long) {
        val currentTime = System.currentTimeMillis()
        frameCount++
        if (lastFrameTime > 0) {
            frameTimeList.add(currentTime - lastFrameTime)
            if (frameTimeList.size > 60) frameTimeList.removeAt(0)
        }
        lastFrameTime = currentTime
    }
    
    private fun sendStatusBroadcast(status: String, message: String, url: String = rtmpUrl) {
        val intent = Intent(ACTION_CONNECTION_STATUS).apply {
            putExtra(EXTRA_STATUS, status)
            putExtra(EXTRA_MESSAGE, message)
            putExtra(EXTRA_URL, url)
        }
        sendBroadcast(intent)
    }
    
    private fun startPerformanceMonitoring() {
        frameCount = 0
        lastFrameTime = System.currentTimeMillis()
        lastStatsTime = System.currentTimeMillis()
        frameTimeList.clear()
        
        performanceHandler.postDelayed(object : Runnable {
            override fun run() {
                if (isStreaming) {
                    val currentTime = System.currentTimeMillis()
                    val elapsed = (currentTime - lastStatsTime) / 1000.0
                    if (elapsed > 0.1) {
                        val fps = frameCount / elapsed
                        Log.i(TAG, "FPS: %.1f".format(fps))
                        frameCount = 0
                        lastStatsTime = currentTime
                    }
                    performanceHandler.postDelayed(this, 5000)
                }
            }
        }, 5000)
    }
    
    private fun stopPerformanceMonitoring() {
        performanceHandler.removeCallbacksAndMessages(null)
    }
}