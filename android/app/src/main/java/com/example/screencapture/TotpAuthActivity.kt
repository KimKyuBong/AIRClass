package com.example.screencapture

import android.content.Intent
import android.os.Bundle
import android.util.Log
import android.view.View
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import org.json.JSONObject
import java.io.OutputStreamWriter
import java.net.HttpURLConnection
import java.net.URL
import java.util.concurrent.Executors

/**
 * TOTP 6자리 코드 입력 후 device-token API 호출, 토큰 저장 후 MainActivity로 이동.
 */
class TotpAuthActivity : AppCompatActivity() {

    companion object {
        const val EXTRA_SERVER_IP = "server_ip"
        const val EXTRA_SERVER_PORT = "server_port"
        private const val TAG = "TotpAuth"
        private const val DEFAULT_API_PORT = 8000
    }

    private lateinit var totpCodeInput: EditText
    private lateinit var btnVerify: Button
    private lateinit var errorText: TextView
    private lateinit var serverInfoText: TextView

    private var serverIp: String = ""
    private var serverPort: Int = DEFAULT_API_PORT
    private val executor = Executors.newSingleThreadExecutor()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_totp_auth)

        serverIp = intent.getStringExtra(EXTRA_SERVER_IP).orEmpty()
        serverPort = intent.getIntExtra(EXTRA_SERVER_PORT, DEFAULT_API_PORT)
        if (serverPort <= 0) serverPort = DEFAULT_API_PORT

        totpCodeInput = findViewById(R.id.totpCodeInput)
        btnVerify = findViewById(R.id.btnVerify)
        errorText = findViewById(R.id.errorText)
        serverInfoText = findViewById(R.id.serverInfoText)

        serverInfoText.text = "서버: $serverIp:$serverPort"

        // 서버 IP가 없으면 설정에서 읽기 (QR 스캔 후 진입 시)
        if (serverIp.isEmpty()) {
            serverIp = getSharedPreferences("settings", MODE_PRIVATE).getString("server_ip", "").orEmpty()
            serverInfoText.text = "서버: $serverIp:$serverPort"
        }

        btnVerify.setOnClickListener {
            val code = totpCodeInput.text.toString().trim()
            if (code.length != 6) {
                showError("6자리 코드를 입력하세요.")
                return@setOnClickListener
            }
            if (serverIp.isEmpty()) {
                showError("서버 주소가 없습니다.")
                return@setOnClickListener
            }
            setLoading(true)
            executor.execute { requestDeviceToken(code) }
        }
    }

    private fun requestDeviceToken(totpCode: String) {
        val baseUrl = "http://$serverIp:$serverPort"
        val url = URL("$baseUrl/api/auth/device-token")
        var conn: HttpURLConnection? = null
        try {
            conn = url.openConnection() as HttpURLConnection
            conn.requestMethod = "POST"
            conn.setRequestProperty("Content-Type", "application/json")
            conn.doOutput = true
            conn.connectTimeout = 10_000
            conn.readTimeout = 10_000

            val body = JSONObject().apply { put("totp_code", totpCode) }
            OutputStreamWriter(conn.outputStream).use { it.write(body.toString()) }

            val code = conn.responseCode
            if (code in 200..299) {
                val response = conn.inputStream.bufferedReader().readText()
                val json = JSONObject(response)
                val token = json.optString("token")
                val expiresIn = json.optInt("expires_in_minutes", 15)
                if (token.isNotEmpty()) {
                    saveTokenAndFinish(token, expiresIn)
                    return
                }
            }
            val errorBody = conn.errorStream?.bufferedReader()?.readText().orEmpty()
            runOnUiThread { onTokenError(code, errorBody) }
        } catch (e: Exception) {
            Log.e(TAG, "device-token request failed", e)
            runOnUiThread { onTokenError(-1, e.message ?: "연결 실패") }
        } finally {
            conn?.disconnect()
        }
    }

    private fun saveTokenAndFinish(token: String, expiresInMinutes: Int) {
        val prefs = getSharedPreferences("settings", MODE_PRIVATE)
        prefs.edit().apply {
            putString("device_token", token)
            putString("server_ip", serverIp)
            putInt("server_port", serverPort)
            putLong("device_token_expires_at", System.currentTimeMillis() + expiresInMinutes * 60_000L)
            apply()
        }
        runOnUiThread {
            setLoading(false)
            Toast.makeText(this, "연동되었습니다.", Toast.LENGTH_SHORT).show()
            val intent = Intent(this, MainActivity::class.java).apply {
                putExtra("mode", "totp")
                putExtra("auto_start", intent.getBooleanExtra("auto_start", false))
            }
            startActivity(intent)
            finish()
        }
    }

    private fun onTokenError(code: Int, message: String) {
        setLoading(false)
        val detail = when (code) {
            403 -> "TOTP 코드가 올바르지 않거나 만료되었습니다."
            503 -> "서버에 TOTP가 설정되지 않았습니다."
            else -> if (message.isNotEmpty()) message else "연결할 수 없습니다. 서버 주소와 네트워크를 확인하세요."
        }
        showError(detail)
    }

    private fun showError(msg: String) {
        errorText.text = msg
        errorText.visibility = View.VISIBLE
    }

    private fun setLoading(loading: Boolean) {
        runOnUiThread {
            btnVerify.isEnabled = !loading
            totpCodeInput.isEnabled = !loading
            if (loading) errorText.visibility = View.GONE
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        executor.shutdown()
    }
}
