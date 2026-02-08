package com.example.screencapture

import android.content.Intent
import android.net.nsd.NsdManager
import android.net.nsd.NsdServiceInfo
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.util.Log
import android.view.View
import android.widget.AdapterView
import android.view.LayoutInflater
import android.view.ViewGroup
import android.widget.ArrayAdapter
import android.widget.ListView
import android.widget.ProgressBar
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import java.net.InetAddress
import java.util.concurrent.ConcurrentHashMap

/**
 * mDNS로 _airclass._tcp 서비스를 검색하고, 선택 시 해당 서버 IP로 TOTP 인증 화면으로 이동합니다.
 */
class MdnsDiscoveryActivity : AppCompatActivity() {

    companion object {
        private const val TAG = "MdnsDiscovery"
        private const val SERVICE_TYPE = "_airclass._tcp."
        private const val DISCOVERY_TIMEOUT_MS = 15_000L
    }

    private var nsdManager: NsdManager? = null
    private var discoveryListener: NsdManager.DiscoveryListener? = null
    private val discoveredServers = ConcurrentHashMap<String, ServerEntry>()
    private var listAdapter: ServerListAdapter? = null
    private val mainHandler = Handler(Looper.getMainLooper())

    private lateinit var progressBar: ProgressBar
    private lateinit var statusText: TextView
    private lateinit var listServers: ListView
    private lateinit var btnRetry: android.widget.Button

    data class ServerEntry(
        val name: String,
        val host: String,
        val port: Int
    )

    private inner class ServerListAdapter(
        context: android.content.Context,
        items: MutableList<ServerEntry>
    ) : ArrayAdapter<ServerEntry>(context, R.layout.item_server, items) {
        override fun getView(position: Int, convertView: View?, parent: ViewGroup): View {
            val view = convertView ?: LayoutInflater.from(context).inflate(R.layout.item_server, parent, false)
            val item = getItem(position) ?: return view
            view.findViewById<TextView>(R.id.serverName).text = item.name
            view.findViewById<TextView>(R.id.serverAddress).text = "${item.host}:${item.port}"
            return view
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_mdns_discovery)

        progressBar = findViewById(R.id.progressBar)
        statusText = findViewById(R.id.statusText)
        listServers = findViewById(R.id.listServers)
        btnRetry = findViewById(R.id.btnRetry)

        listAdapter = ServerListAdapter(this, mutableListOf())
        listServers.adapter = listAdapter
        listServers.onItemClickListener = AdapterView.OnItemClickListener { _, _, position, _ ->
            val entry = listAdapter?.getItem(position) ?: return@OnItemClickListener
            stopDiscovery()
            saveServerAndStartTotp(entry.host, entry.port)
        }

        btnRetry.setOnClickListener {
            discoveredServers.clear()
            listAdapter?.clear()
            listAdapter?.notifyDataSetChanged()
            progressBar.visibility = View.VISIBLE
            listServers.visibility = View.GONE
            statusText.text = "검색 중..."
            btnRetry.visibility = View.GONE
            startDiscovery()
        }

        startDiscovery()
        mainHandler.postDelayed({ onDiscoveryTimeout() }, DISCOVERY_TIMEOUT_MS)
    }

    override fun onDestroy() {
        super.onDestroy()
        stopDiscovery()
        mainHandler.removeCallbacksAndMessages(null)
    }

    private fun startDiscovery() {
        nsdManager = (getSystemService(NSD_SERVICE) as? NsdManager)
        if (nsdManager == null) {
            showError("NSD를 사용할 수 없습니다.")
            return
        }

        discoveryListener = object : NsdManager.DiscoveryListener {
            override fun onDiscoveryStarted(serviceType: String?) {
                Log.d(TAG, "Discovery started: $serviceType")
                runOnUiThread { statusText.text = "같은 Wi‑Fi에서 서버를 찾는 중..." }
            }

            override fun onServiceFound(service: NsdServiceInfo?) {
                if (service == null) return
                Log.d(TAG, "Service found: ${service.serviceName} type=${service.serviceType}")
                nsdManager?.resolveService(service, object : NsdManager.ResolveListener {
                    override fun onResolveFailed(serviceInfo: NsdServiceInfo?, errorCode: Int) {
                        Log.w(TAG, "Resolve failed: ${serviceInfo?.serviceName} code=$errorCode")
                    }
                    override fun onServiceResolved(serviceInfo: NsdServiceInfo?) {
                        if (serviceInfo == null) return
                        val host: String = serviceInfo.host?.hostAddress ?: return
                        val port = serviceInfo.port
                        val name = serviceInfo.serviceName ?: "AIRClass"
                        val key = "$host:$port"
                        if (discoveredServers.putIfAbsent(key, ServerEntry(name, host, port)) == null) {
                            mainHandler.post { addServerAndUpdateList(ServerEntry(name, host, port)) }
                        }
                    }
                })
            }

            override fun onServiceLost(service: NsdServiceInfo?) {
                Log.d(TAG, "Service lost: ${service?.serviceName}")
            }

            override fun onDiscoveryStopped(serviceType: String?) {
                Log.d(TAG, "Discovery stopped: $serviceType")
            }

            override fun onStartDiscoveryFailed(serviceType: String?, errorCode: Int) {
                Log.e(TAG, "Start discovery failed: $serviceType code=$errorCode")
                runOnUiThread { showError("검색을 시작할 수 없습니다. Wi‑Fi가 켜져 있는지 확인하세요.") }
            }

            override fun onStopDiscoveryFailed(serviceType: String?, errorCode: Int) {
                Log.e(TAG, "Stop discovery failed: $serviceType code=$errorCode")
            }
        }

        try {
            @Suppress("DEPRECATION")
            nsdManager?.discoverServices(SERVICE_TYPE, NsdManager.PROTOCOL_DNS_SD, discoveryListener!!)
        } catch (e: Exception) {
            Log.e(TAG, "discoverServices failed", e)
            showError("검색 오류: ${e.message}")
        }
    }

    private fun addServerAndUpdateList(entry: ServerEntry) {
        listAdapter?.add(entry)
        listAdapter?.notifyDataSetChanged()
        progressBar.visibility = View.GONE
        listServers.visibility = View.VISIBLE
        statusText.text = "서버를 선택하세요 (${listAdapter?.count ?: 0}개 발견)"
    }

    private fun onDiscoveryTimeout() {
        if (discoveredServers.isEmpty()) {
            runOnUiThread {
                progressBar.visibility = View.GONE
                statusText.text = "서버를 찾지 못했습니다. 같은 Wi‑Fi에 연결되어 있는지 확인하세요."
                btnRetry.visibility = View.VISIBLE
            }
        }
    }

    private fun stopDiscovery() {
        try {
            discoveryListener?.let { nsdManager?.stopServiceDiscovery(it) }
        } catch (e: Exception) {
            Log.w(TAG, "stopServiceDiscovery", e)
        }
        discoveryListener = null
    }

    private fun showError(message: String) {
        progressBar.visibility = View.GONE
        listServers.visibility = View.GONE
        statusText.text = message
        btnRetry.visibility = View.VISIBLE
        Toast.makeText(this, message, Toast.LENGTH_LONG).show()
    }

    private fun saveServerAndStartTotp(host: String, port: Int) {
        getSharedPreferences("settings", MODE_PRIVATE).edit().apply {
            putString("server_ip", host)
            putInt("server_port", port)
            apply()
        }
        val intent = Intent(this, TotpAuthActivity::class.java).apply {
            putExtra(TotpAuthActivity.EXTRA_SERVER_IP, host)
            putExtra(TotpAuthActivity.EXTRA_SERVER_PORT, port)
            putExtra("auto_start", true)
        }
        startActivity(intent)
        finish()
    }
}
