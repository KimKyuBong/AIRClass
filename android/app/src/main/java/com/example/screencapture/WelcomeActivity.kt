package com.example.screencapture

import android.content.Intent
import android.os.Bundle
import android.widget.Button
import androidx.appcompat.app.AppCompatActivity

class WelcomeActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_welcome)

        val devButton = findViewById<Button>(R.id.btnDev)
        val qrButton = findViewById<Button>(R.id.btnQR)

        devButton.setOnClickListener {
            // DEV 모드: 수동 IP 입력 (기존 MainActivity로 이동)
            val intent = Intent(this, MainActivity::class.java)
            intent.putExtra("mode", "dev")
            startActivity(intent)
        }

        qrButton.setOnClickListener {
            // QR 모드: QR 스캔으로 서버 연결
            val intent = Intent(this, QRScanActivity::class.java)
            startActivity(intent)
        }
    }
}
