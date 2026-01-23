package com.example.screencapture

import android.Manifest
import android.app.Activity
import android.app.AlertDialog
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageManager
import android.graphics.Color
import android.media.projection.MediaProjectionManager
import android.os.Build
import android.os.Bundle
import android.view.LayoutInflater
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.EditText
import android.widget.Spinner
import android.widget.TextView
import android.net.Uri
import android.provider.Settings
import android.widget.Toast
import android.util.Log
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.activity.result.contract.ActivityResultContracts
import com.example.screencapture.service.ScreenCaptureService
import com.google.android.material.floatingactionbutton.FloatingActionButton
import androidx.appcompat.widget.SwitchCompat

class MainActivity : AppCompatActivity() {

    private lateinit var serverIpInput: EditText
    private lateinit var startButton: Button
    private lateinit var stopButton: Button
    private lateinit var statusText: TextView
    private lateinit var fabOptions: FloatingActionButton

    private val mediaProjectionManager by lazy {
        getSystemService(MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
    }
    
    // 연결 상태를 받기 위한 BroadcastReceiver
    private val connectionStatusReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) {
            val status = intent?.getStringExtra(ScreenCaptureService.EXTRA_STATUS) ?: return
            val message = intent.getStringExtra(ScreenCaptureService.EXTRA_MESSAGE) ?: ""
            val url = intent.getStringExtra(ScreenCaptureService.EXTRA_URL) ?: ""
            
            updateConnectionStatus(status, message, url)
        }
    }

    private val screenCaptureLauncher = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { result ->
        if (result.resultCode == Activity.RESULT_OK) {
            result.data?.let { data ->
                Toast.makeText(this, "✅ 권한 승인됨! 스트리밍 시작...", Toast.LENGTH_SHORT).show()
                startCaptureService(data)
            } ?: run {
                Toast.makeText(this, "❌ 데이터가 없습니다", Toast.LENGTH_SHORT).show()
                updateUI(false)
            }
        } else {
            Toast.makeText(this, "❌ 화면 캡처 권한이 거부되었습니다. [시작] 버튼을 다시 누르고 '지금 시작'을 선택하세요.", Toast.LENGTH_LONG).show()
            updateUI(false)
        }
    }

    private val overlayPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) {
        if (Settings.canDrawOverlays(this)) {
            Toast.makeText(this, "✅ 오버레이 권한 승인됨", Toast.LENGTH_SHORT).show()
            checkPermissionsAndStart()
        } else {
            Toast.makeText(this, "❌ 오버레이 권한이 거부되었습니다. 테두리 표시가 제한됩니다.", Toast.LENGTH_LONG).show()
            // 권한 없어도 스트리밍은 시작
            checkPermissionsAndStart()
        }
    }

    private val multiplePermissionsLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { permissions ->
        // 권한 결과 로깅
        permissions.forEach { (permission, granted) ->
            Log.d("MainActivity", "Permission $permission: ${if (granted) "GRANTED" else "DENIED"}")
        }
        
        // 권한 결과 확인
        val deniedPermissions = permissions.filter { !it.value }.keys
        
        if (deniedPermissions.isEmpty()) {
            // 모든 권한이 승인됨 - 다시 한 번 확인
            Log.d("MainActivity", "All permissions granted, verifying...")
            
            // 권한이 실제로 부여되었는지 재확인
            val allReallyGranted = permissions.keys.all { permission ->
                val isGranted = ContextCompat.checkSelfPermission(this, permission) == PackageManager.PERMISSION_GRANTED
                if (!isGranted) {
                    Log.w("MainActivity", "Permission $permission was reported granted but checkSelfPermission says denied!")
                }
                isGranted
            }
            
            if (allReallyGranted) {
                Log.d("MainActivity", "Permissions verified, requesting screen capture")
                requestScreenCapture()
            } else {
                Log.e("MainActivity", "Permission verification failed, retrying...")
                // 권한이 실제로 부여되지 않았으므로 다시 요청
                checkPermissionsAndStart()
            }
        } else {
            // 일부 권한이 거부됨
            val deniedList = deniedPermissions.joinToString(", ")
            Log.w("MainActivity", "Some permissions denied: $deniedList")
            
            Toast.makeText(
                this, 
                "다음 권한이 필요합니다: $deniedList\n설정에서 권한을 허용해주세요.", 
                Toast.LENGTH_LONG
            ).show()
            
            // 권한이 영구적으로 거부되었는지 확인
            val shouldShowRationale = deniedPermissions.any { permission ->
                shouldShowRequestPermissionRationale(permission)
            }
            
            if (!shouldShowRationale) {
                // 사용자가 "다시 묻지 않음"을 선택한 경우
                AlertDialog.Builder(this)
                    .setTitle("권한 필요")
                    .setMessage("앱을 사용하려면 다음 권한이 필요합니다:\n$deniedList\n\n설정 > 앱 > Screen Capture > 권한에서 권한을 허용해주세요.")
                    .setPositiveButton("설정으로 이동") { _, _ ->
                        val intent = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS).apply {
                            data = Uri.fromParts("package", packageName, null)
                        }
                        startActivity(intent)
                    }
                    .setNegativeButton("취소", null)
                    .show()
            } else {
                // 다시 요청 가능한 경우
                updateUI(false)
            }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        initViews()
        setupListeners()
        registerConnectionReceiver()
        
        // QR 스캔으로 들어온 경우 자동 시작
        if (intent.getBooleanExtra("auto_start", false)) {
            // 약간의 딜레이 후 자동 시작 (UI 준비 대기)
            android.os.Handler(android.os.Looper.getMainLooper()).postDelayed({
                startButton.performClick()
            }, 500)
        }
    }
    
    override fun onResume() {
        super.onResume()
        // 앱이 다시 활성화될 때 권한 상태 확인
        // (설정에서 권한을 변경한 후 돌아온 경우 대비)
        if (::startButton.isInitialized && startButton.isEnabled) {
            // 시작 버튼이 활성화되어 있으면 권한이 부여된 상태
            // 하지만 실제로 권한이 있는지 재확인
            val permissions = mutableListOf(Manifest.permission.RECORD_AUDIO)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                permissions.add(Manifest.permission.POST_NOTIFICATIONS)
            }
            
            val allGranted = permissions.all {
                ContextCompat.checkSelfPermission(this, it) == PackageManager.PERMISSION_GRANTED
            }
            
            if (!allGranted) {
                Log.w("MainActivity", "Permissions were revoked, updating UI")
                updateUI(false)
            }
        }
    }
    
    override fun onDestroy() {
        super.onDestroy()
        unregisterConnectionReceiver()
    }
    
    private fun registerConnectionReceiver() {
        val filter = IntentFilter(ScreenCaptureService.ACTION_CONNECTION_STATUS)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            registerReceiver(connectionStatusReceiver, filter, RECEIVER_NOT_EXPORTED)
        } else {
            registerReceiver(connectionStatusReceiver, filter)
        }
    }
    
    private fun unregisterConnectionReceiver() {
        try {
            unregisterReceiver(connectionStatusReceiver)
        } catch (e: Exception) {
            // Already unregistered
        }
    }

    private fun initViews() {
        // 기존 ID 재사용 (serverUrlInput -> serverIpInput)
        // XML을 수정하지 않고 기존 ID를 그대로 사용하되 의미만 변경
        serverIpInput = findViewById(R.id.serverUrlInput)
        
        // interval 입력창은 숨기거나 무시 (ID는 유지)
        val intervalInput: EditText = findViewById(R.id.captureIntervalInput)
        intervalInput.isEnabled = false
        intervalInput.hint = "비디오 모드에서는 사용 안함"

        startButton = findViewById(R.id.startButton)
        stopButton = findViewById(R.id.stopButton)
        statusText = findViewById(R.id.statusText)
        fabOptions = findViewById(R.id.fabOptions)

        // 기본 IP 설정 (Android 에뮬레이터용)
        serverIpInput.setText("10.0.2.2")
        
        updateUI(false)
    }

    private fun setupListeners() {
        startButton.setOnClickListener {
            val serverIp = serverIpInput.text.toString()

            if (serverIp.isEmpty()) {
                Toast.makeText(this, "서버 IP를 입력하세요", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            // SharedPreferences에 설정 저장
            getSharedPreferences("settings", MODE_PRIVATE).edit().apply {
                putString("server_ip", serverIp)
                apply()
            }

            // 오버레이 권한 확인 (Android M 이상)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M && !Settings.canDrawOverlays(this)) {
                val intent = Intent(
                    Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                    Uri.parse("package:$packageName")
                )
                overlayPermissionLauncher.launch(intent)
            } else {
                checkPermissionsAndStart()
            }
        }

        stopButton.setOnClickListener {
            stopCaptureService()
        }
        
        fabOptions.setOnClickListener {
            showOptionsDialog()
        }
    }

    private fun checkPermissionsAndStart() {
        val permissions = mutableListOf(Manifest.permission.RECORD_AUDIO)
        
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            permissions.add(Manifest.permission.POST_NOTIFICATIONS)
        }

        val neededPermissions = permissions.filter {
            val granted = ContextCompat.checkSelfPermission(this, it) == PackageManager.PERMISSION_GRANTED
            if (!granted) {
                Log.d("MainActivity", "Permission needed: $it")
            }
            !granted
        }

        if (neededPermissions.isEmpty()) {
            // 모든 권한이 부여됨
            Log.d("MainActivity", "All permissions granted, requesting screen capture")
            requestScreenCapture()
        } else {
            // 권한 요청 필요
            Log.d("MainActivity", "Requesting permissions: ${neededPermissions.joinToString()}")
            multiplePermissionsLauncher.launch(neededPermissions.toTypedArray())
        }
    }

    private fun requestScreenCapture() {
        val captureIntent = mediaProjectionManager.createScreenCaptureIntent()
        screenCaptureLauncher.launch(captureIntent)
    }

    private fun startCaptureService(data: Intent) {
        val serviceIntent = Intent(this, ScreenCaptureService::class.java).apply {
            putExtra("resultCode", Activity.RESULT_OK)
            putExtra("data", data)
        }
        
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(serviceIntent)
        } else {
            startService(serviceIntent)
        }

        updateUI(true)
        Toast.makeText(this, "화면 송출 시작", Toast.LENGTH_SHORT).show()
    }

    private fun stopCaptureService() {
        val serviceIntent = Intent(this, ScreenCaptureService::class.java)
        stopService(serviceIntent)
        updateUI(false)
        Toast.makeText(this, "화면 송출 중지", Toast.LENGTH_SHORT).show()
    }

    private fun updateUI(isRunning: Boolean) {
        startButton.isEnabled = !isRunning
        stopButton.isEnabled = isRunning
        serverIpInput.isEnabled = !isRunning
        
        if (!isRunning) {
            statusText.text = "대기 중"
            statusText.setTextColor(Color.GRAY)
        }
    }
    
    private fun updateConnectionStatus(status: String, message: String, url: String) {
        runOnUiThread {
            when (status) {
                ScreenCaptureService.STATUS_STARTING -> {
                    statusText.text = "📡 $message\n🔗 $url"
                    statusText.setTextColor(Color.parseColor("#FF9800")) // Orange
                }
                ScreenCaptureService.STATUS_CONNECTING -> {
                    statusText.text = "🔄 $message\n🔗 $url"
                    statusText.setTextColor(Color.parseColor("#2196F3")) // Blue
                }
                ScreenCaptureService.STATUS_CONNECTED -> {
                    statusText.text = "✅ $message\n🔗 $url"
                    statusText.setTextColor(Color.parseColor("#4CAF50")) // Green
                }
                ScreenCaptureService.STATUS_FAILED -> {
                    statusText.text = "❌ $message\n🔗 $url"
                    statusText.setTextColor(Color.parseColor("#F44336")) // Red
                    Toast.makeText(this, message, Toast.LENGTH_LONG).show()
                }
                ScreenCaptureService.STATUS_DISCONNECTED -> {
                    statusText.text = "🔌 $message"
                    statusText.setTextColor(Color.parseColor("#FF9800")) // Orange
                }
            }
        }
    }
    
    private fun showOptionsDialog() {
        val dialogView = LayoutInflater.from(this).inflate(R.layout.dialog_streaming_options, null)
        
        // 다이얼로그 내 UI 요소 찾기
        val rgAspectRatio = dialogView.findViewById<android.widget.RadioGroup>(R.id.rg_aspect_ratio)
        val rbAspect16_9 = dialogView.findViewById<android.widget.RadioButton>(R.id.rb_aspect_16_9)
        val rbAspectDevice = dialogView.findViewById<android.widget.RadioButton>(R.id.rb_aspect_device)
        val resolutionSpinner = dialogView.findViewById<Spinner>(R.id.spinner_resolution)
        val fpsSpinner = dialogView.findViewById<Spinner>(R.id.fpsSpinner)
        val bitrateSpinner = dialogView.findViewById<Spinner>(R.id.bitrateSpinner)
        val audioSwitch = dialogView.findViewById<SwitchCompat>(R.id.audioSwitch)
        val autoReconnectSwitch = dialogView.findViewById<SwitchCompat>(R.id.autoReconnectSwitch)
        
        // 해상도 옵션 설정
        val resolutions = arrayOf("FHD (1920x1080)", "QHD (2560x1440)", "4K (3840x2160)")
        resolutionSpinner.adapter = ArrayAdapter(this, android.R.layout.simple_spinner_dropdown_item, resolutions)
        
        // FPS 옵션 설정
        val fpsOptions = arrayOf("15 fps", "24 fps", "30 fps", "60 fps")
        fpsSpinner.adapter = ArrayAdapter(this, android.R.layout.simple_spinner_dropdown_item, fpsOptions)
        
        // 비트레이트 옵션 설정
        val bitrateOptions = arrayOf("5.0 Mbps", "8.0 Mbps", "10.0 Mbps", "15.0 Mbps", "20.0 Mbps", "25.0 Mbps", "30.0 Mbps")
        bitrateSpinner.adapter = ArrayAdapter(this, android.R.layout.simple_spinner_dropdown_item, bitrateOptions)
        
        // 저장된 설정 불러오기
        val prefs = getSharedPreferences("streaming_settings", MODE_PRIVATE)
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
        
        // 라디오 버튼 리스너
        rgAspectRatio.setOnCheckedChangeListener { _, checkedId ->
            if (checkedId == R.id.rb_aspect_device) {
                resolutionSpinner.isEnabled = false
                resolutionSpinner.alpha = 0.5f
            } else {
                resolutionSpinner.isEnabled = true
                resolutionSpinner.alpha = 1.0f
            }
        }

        resolutionSpinner.setSelection(prefs.getInt("resolution", 0)) // 기본 FHD
        fpsSpinner.setSelection(prefs.getInt("fps", 2)) // 기본 30fps
        bitrateSpinner.setSelection(prefs.getInt("bitrate", 1)) // 기본 8.0 Mbps
        audioSwitch.isChecked = prefs.getBoolean("audio_enabled", true)
        autoReconnectSwitch.isChecked = prefs.getBoolean("auto_reconnect", true)
        
        // 다이얼로그 생성
        val dialog = AlertDialog.Builder(this)
        .setView(dialogView)
        .create()
        
        // 저장 버튼 클릭
        dialogView.findViewById<Button>(R.id.saveButton).setOnClickListener {
            // 현재 설정값 읽기
            val newUseNative = rbAspectDevice.isChecked
            val newResIndex = resolutionSpinner.selectedItemPosition
            val newFpsIndex = fpsSpinner.selectedItemPosition
            val newBitrateIndex = bitrateSpinner.selectedItemPosition
            
            // 스트리밍 중인지 확인 (Stop 버튼이 활성화되어 있으면 스트리밍 중)
            val isStreaming = stopButton.isEnabled
            
            if (isStreaming) {
                // 스트리밍 중이면 서비스에 변경 요청 전달
                val updateIntent = Intent(this, ScreenCaptureService::class.java).apply {
                    action = ScreenCaptureService.ACTION_UPDATE_SETTINGS
                    putExtra(ScreenCaptureService.EXTRA_USE_NATIVE_RES, newUseNative)
                    putExtra(ScreenCaptureService.EXTRA_RESOLUTION_INDEX, newResIndex)
                    putExtra(ScreenCaptureService.EXTRA_FPS, newFpsIndex)
                    putExtra(ScreenCaptureService.EXTRA_BITRATE, newBitrateIndex)
                }
                startService(updateIntent)
                Toast.makeText(this, "설정 변경 요청을 보냈습니다.", Toast.LENGTH_SHORT).show()
            } else {
                // 스트리밍 중이 아니면 그냥 저장
                prefs.edit().apply {
                    putBoolean("use_native_res", newUseNative)
                    putInt("resolution", newResIndex)
                    putInt("fps", newFpsIndex)
                    putInt("bitrate", newBitrateIndex)
                    putBoolean("audio_enabled", audioSwitch.isChecked)
                    putBoolean("auto_reconnect", autoReconnectSwitch.isChecked)
                    apply()
                }
                Toast.makeText(this, "설정이 저장되었습니다.", Toast.LENGTH_SHORT).show()
            }
            
            dialog.dismiss()
        }
        
        // 취소 버튼 클릭
        dialogView.findViewById<Button>(R.id.cancelButton).setOnClickListener {
            dialog.dismiss()
        }
        
        dialog.show()
    }
}
