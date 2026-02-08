package com.example.screencapture

import android.Manifest
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Bundle
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import com.journeyapps.barcodescanner.ScanContract
import com.journeyapps.barcodescanner.ScanOptions

class QRScanActivity : AppCompatActivity() {

    private val cameraPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { isGranted ->
        if (isGranted) {
            startQRScanner()
        } else {
            Toast.makeText(this, "카메라 권한이 필요합니다", Toast.LENGTH_LONG).show()
            finish()
        }
    }

    private val barcodeLauncher = registerForActivityResult(ScanContract()) { result ->
        if (result.contents != null) {
            val serverIp = result.contents
            
            // IP 주소 유효성 검사 (간단)
            if (isValidIP(serverIp)) {
                // SharedPreferences에 저장
                getSharedPreferences("settings", MODE_PRIVATE).edit().apply {
                    putString("server_ip", serverIp)
                    apply()
                }
                
                Toast.makeText(this, "서버 연결: $serverIp", Toast.LENGTH_SHORT).show()
                
                // TOTP 인증 후 MainActivity로 이동 (자동 시작 옵션 전달)
                val intent = Intent(this, TotpAuthActivity::class.java).apply {
                    putExtra(TotpAuthActivity.EXTRA_SERVER_IP, serverIp)
                    putExtra(TotpAuthActivity.EXTRA_SERVER_PORT, 8000)
                    putExtra("auto_start", true)
                }
                startActivity(intent)
                finish()
            } else {
                Toast.makeText(this, "유효하지 않은 IP 주소입니다", Toast.LENGTH_LONG).show()
                finish()
            }
        } else {
            // 스캔 취소
            finish()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        // 카메라 권한 확인
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA) 
            == PackageManager.PERMISSION_GRANTED) {
            startQRScanner()
        } else {
            cameraPermissionLauncher.launch(Manifest.permission.CAMERA)
        }
    }

    private fun startQRScanner() {
        val options = ScanOptions()
        options.setDesiredBarcodeFormats(ScanOptions.QR_CODE)
        options.setPrompt("서버 QR 코드를 스캔하세요")
        options.setBeepEnabled(true)
        options.setBarcodeImageEnabled(true)
        options.setOrientationLocked(false)
        
        barcodeLauncher.launch(options)
    }

    private fun isValidIP(ip: String): Boolean {
        // 간단한 IP 검증 (xxx.xxx.xxx.xxx 형식)
        val parts = ip.split(".")
        if (parts.size != 4) return false
        
        return parts.all { part ->
            part.toIntOrNull()?.let { it in 0..255 } ?: false
        }
    }
}
