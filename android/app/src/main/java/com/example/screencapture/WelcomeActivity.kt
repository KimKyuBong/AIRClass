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
        val mdnsButton = findViewById<Button>(R.id.btnMdns)

        devButton.setOnClickListener {
            // 테스트용: 자동으로 서버 IP 설정하고 접속 시도
            val prefs = getSharedPreferences("settings", MODE_PRIVATE)
            prefs.edit().apply {
                putString("server_ip", "192.168.0.127")
                putString("node_password", "test")
                apply()
            }
            
            val intent = Intent(this, MainActivity::class.java)
            intent.putExtra("mode", "dev")
            intent.putExtra("auto_start", true) // 자동 시작 플래그
            startActivity(intent)
        }

        qrButton.setOnClickListener {
            val intent = Intent(this, QRScanActivity::class.java)
            startActivity(intent)
        }

        mdnsButton.setOnClickListener {
            val intent = Intent(this, MdnsDiscoveryActivity::class.java)
            startActivity(intent)
        }
    }
}
