<script>
  import { onMount, onDestroy } from 'svelte';
  
  // Configuration
  const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';
  const REFRESH_INTERVAL = 5000; // 5 seconds
  
  // State
  let clusterData = null;
  let loading = true;
  let error = null;
  let refreshTimer = null;
  let autoRefresh = true;
  
  // Fetch cluster status
  async function fetchClusterStatus() {
    try {
      const response = await fetch(`${BACKEND_URL}/cluster/nodes`);
      if (!response.ok) throw new Error('Failed to fetch cluster status');
      clusterData = await response.json();
      error = null;
    } catch (err) {
      error = err.message;
      console.error('Cluster status error:', err);
    } finally {
      loading = false;
    }
  }
  
  // Calculate cluster-wide stats
  $: totalCapacity = clusterData?.nodes?.reduce((sum, node) => sum + node.max_connections, 0) || 0;
  $: totalConnections = clusterData?.nodes?.reduce((sum, node) => sum + node.current_connections, 0) || 0;
  $: activeNodes = clusterData?.nodes?.filter(n => n.status === 'healthy').length || 0;
  $: averageLoad = clusterData?.nodes?.length > 0 
    ? clusterData.nodes.reduce((sum, node) => sum + ((node.current_connections / node.max_connections) * 100 || 0), 0) / clusterData.nodes.length 
    : 0;
  
  // Get status color
  function getStatusColor(status) {
    switch(status) {
      case 'healthy': return 'text-green-600';
      case 'offline': return 'text-red-600';
      case 'unhealthy': return 'text-yellow-600';
      default: return 'text-gray-600';
    }
  }
  
  // Get load color
  function getLoadColor(percentage) {
    if (percentage >= 90) return 'bg-red-500';
    if (percentage >= 70) return 'bg-yellow-500';
    return 'bg-green-500';
  }
  
  // Format date
  function formatDate(dateString) {
    return new Date(dateString).toLocaleString();
  }
  
  // Start auto-refresh
  function startAutoRefresh() {
    if (refreshTimer) clearInterval(refreshTimer);
    refreshTimer = setInterval(fetchClusterStatus, REFRESH_INTERVAL);
  }
  
  // Stop auto-refresh
  function stopAutoRefresh() {
    if (refreshTimer) {
      clearInterval(refreshTimer);
      refreshTimer = null;
    }
  }
  
  // Toggle auto-refresh
  function toggleAutoRefresh() {
    autoRefresh = !autoRefresh;
    if (autoRefresh) {
      startAutoRefresh();
    } else {
      stopAutoRefresh();
    }
  }
  
  // Lifecycle
  onMount(() => {
    fetchClusterStatus();
    if (autoRefresh) startAutoRefresh();
  });
  
  onDestroy(() => {
    stopAutoRefresh();
  });
</script>

<div class="min-h-screen bg-gray-100 p-8">
  <div class="max-w-7xl mx-auto">
    <!-- Header -->
    <div class="mb-8 flex justify-between items-center">
      <div>
        <h1 class="text-4xl font-bold text-gray-900">AIRClass Admin Dashboard</h1>
        <p class="text-gray-600 mt-2">Cluster monitoring and management</p>
      </div>
      
      <div class="flex gap-4">
        <button 
          on:click={toggleAutoRefresh}
          class="px-4 py-2 rounded-lg {autoRefresh ? 'bg-green-500 text-white' : 'bg-gray-300 text-gray-700'}"
        >
          {autoRefresh ? '🔄 Auto-refresh ON' : '⏸️ Auto-refresh OFF'}
        </button>
        
        <button 
          on:click={fetchClusterStatus}
          class="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
          disabled={loading}
        >
          {loading ? '⏳ Loading...' : '🔄 Refresh Now'}
        </button>
      </div>
    </div>
    
    <!-- Error Message -->
    {#if error}
      <div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-6">
        <strong>Error:</strong> {error}
      </div>
    {/if}
    
    <!-- Loading State -->
    {#if loading && !clusterData}
      <div class="bg-white rounded-lg shadow-lg p-12 text-center">
        <div class="animate-spin rounded-full h-16 w-16 border-b-4 border-blue-500 mx-auto mb-4"></div>
        <p class="text-gray-600">Loading cluster data...</p>
      </div>
    {:else if clusterData}
      <!-- Cluster Summary -->
      <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <div class="bg-white rounded-lg shadow-lg p-6">
          <h3 class="text-gray-500 text-sm font-medium">Total Nodes</h3>
          <p class="text-4xl font-bold text-gray-900 mt-2">{clusterData.nodes.length}</p>
          <p class="text-sm text-green-600 mt-2">{activeNodes} active</p>
        </div>
        
        <div class="bg-white rounded-lg shadow-lg p-6">
          <h3 class="text-gray-500 text-sm font-medium">Total Capacity</h3>
          <p class="text-4xl font-bold text-gray-900 mt-2">{totalCapacity}</p>
          <p class="text-sm text-gray-600 mt-2">max users</p>
        </div>
        
        <div class="bg-white rounded-lg shadow-lg p-6">
          <h3 class="text-gray-500 text-sm font-medium">Current Load</h3>
          <p class="text-4xl font-bold text-gray-900 mt-2">{totalConnections}</p>
          <p class="text-sm text-gray-600 mt-2">active users</p>
        </div>
        
        <div class="bg-white rounded-lg shadow-lg p-6">
          <h3 class="text-gray-500 text-sm font-medium">Average Load</h3>
          <p class="text-4xl font-bold text-gray-900 mt-2">{averageLoad.toFixed(1)}%</p>
          <div class="w-full bg-gray-200 rounded-full h-2 mt-3">
            <div class="{getLoadColor(averageLoad)} h-2 rounded-full" style="width: {averageLoad}%"></div>
          </div>
        </div>
      </div>
      
      <!-- Recommendations -->
      {#if averageLoad > 80}
        <div class="bg-yellow-100 border border-yellow-400 text-yellow-800 px-4 py-3 rounded mb-6">
          <strong>⚠️ WARNING:</strong> Cluster is heavily loaded ({averageLoad.toFixed(1)}%). 
          Consider scaling up: <code class="bg-yellow-200 px-2 py-1 rounded">docker-compose up -d --scale slave=N</code>
        </div>
      {:else if averageLoad < 30 && clusterData.nodes.length > 1}
        <div class="bg-blue-100 border border-blue-400 text-blue-800 px-4 py-3 rounded mb-6">
          <strong>💡 TIP:</strong> Cluster is under-utilized ({averageLoad.toFixed(1)}%). 
          You can scale down to save resources.
        </div>
      {/if}
      
      <!-- Nodes Table -->
      <div class="bg-white rounded-lg shadow-lg overflow-hidden">
        <div class="px-6 py-4 bg-gray-50 border-b border-gray-200">
          <h2 class="text-xl font-semibold text-gray-900">Cluster Nodes</h2>
        </div>
        
        <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
              <tr>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Node</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Load</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Connections</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">URL</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Last Seen</th>
              </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
              {#each clusterData.nodes as node}
                <tr class="hover:bg-gray-50">
                  <td class="px-6 py-4 whitespace-nowrap">
                    <div class="text-sm font-medium text-gray-900">{node.node_name}</div>
                    <div class="text-sm text-gray-500">{node.node_id}</div>
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap">
                    <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full 
                      {node.status === 'healthy' ? 'bg-green-100 text-green-800' : 
                       node.status === 'offline' ? 'bg-red-100 text-red-800' : 
                       'bg-yellow-100 text-yellow-800'}">
                      {node.status}
                    </span>
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap">
                    <div class="text-sm text-gray-900">{((node.current_connections / node.max_connections) * 100 || 0).toFixed(1)}%</div>
                    <div class="w-24 bg-gray-200 rounded-full h-2 mt-1">
                      <div class="{getLoadColor((node.current_connections / node.max_connections) * 100 || 0)} h-2 rounded-full" 
                           style="width: {(node.current_connections / node.max_connections) * 100 || 0}%"></div>
                    </div>
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {node.current_connections} / {node.max_connections}
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap">
                    <div class="text-sm text-blue-600">{node.host}:{node.port}</div>
                    <div class="text-xs text-gray-500">RTMP: {node.rtmp_port} | HLS: {node.hls_port}</div>
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {formatDate(node.last_heartbeat)}
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      </div>
      
      <!-- Last Updated -->
      <div class="mt-4 text-center text-sm text-gray-500">
        Last updated: {new Date().toLocaleString()}
        {#if autoRefresh}
          <span class="ml-2">(auto-refresh every {REFRESH_INTERVAL/1000}s)</span>
        {/if}
      </div>
    {/if}
  </div>
</div>

<style>
  /* Add Tailwind-like utilities if not using Tailwind */
  .min-h-screen { min-height: 100vh; }
  .max-w-7xl { max-width: 80rem; }
  .mx-auto { margin-left: auto; margin-right: auto; }
  /* Add more styles as needed */
</style>
