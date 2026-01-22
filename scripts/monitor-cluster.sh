#!/bin/bash
# ============================================
# AIRClass Cluster Health Monitor
# ============================================
# Real-time monitoring of Master and Slave nodes
#
# Usage:
#   ./scripts/monitor-cluster.sh                    # Monitor once
#   ./scripts/monitor-cluster.sh --watch            # Continuous monitoring
#   ./scripts/monitor-cluster.sh --watch --interval 5  # Custom interval
#   ./scripts/monitor-cluster.sh --json             # JSON output
#   ./scripts/monitor-cluster.sh --alert            # Send alerts on issues

set -e

# ============================================
# Configuration
# ============================================
MASTER_URL="${MASTER_URL:-http://localhost:8000}"
WATCH_MODE=false
WATCH_INTERVAL=10
JSON_OUTPUT=false
ALERT_MODE=false
ALERT_WEBHOOK="${ALERT_WEBHOOK:-}"

# Colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================
# Parse arguments
# ============================================
while [[ $# -gt 0 ]]; do
    case $1 in
        --watch|-w)
            WATCH_MODE=true
            shift
            ;;
        --interval|-i)
            WATCH_INTERVAL="$2"
            shift 2
            ;;
        --json|-j)
            JSON_OUTPUT=true
            shift
            ;;
        --alert|-a)
            ALERT_MODE=true
            shift
            ;;
        --master|-m)
            MASTER_URL="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --watch, -w              Continuous monitoring mode"
            echo "  --interval, -i SECONDS   Watch interval (default: 10)"
            echo "  --json, -j               JSON output format"
            echo "  --alert, -a              Send alerts on issues"
            echo "  --master, -m URL         Master URL (default: http://localhost:8000)"
            echo "  --help, -h               Show this help"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# ============================================
# Helper functions
# ============================================

log_info() {
    if [ "$JSON_OUTPUT" = false ]; then
        echo -e "${BLUE}[INFO]${NC} $1"
    fi
}

log_success() {
    if [ "$JSON_OUTPUT" = false ]; then
        echo -e "${GREEN}[OK]${NC} $1"
    fi
}

log_warning() {
    if [ "$JSON_OUTPUT" = false ]; then
        echo -e "${YELLOW}[WARN]${NC} $1"
    fi
}

log_error() {
    if [ "$JSON_OUTPUT" = false ]; then
        echo -e "${RED}[ERROR]${NC} $1"
    fi
}

send_alert() {
    local message="$1"
    if [ "$ALERT_MODE" = true ] && [ -n "$ALERT_WEBHOOK" ]; then
        curl -s -X POST "$ALERT_WEBHOOK" \
            -H "Content-Type: application/json" \
            -d "{\"text\":\"AIRClass Alert: $message\"}" > /dev/null
    fi
}

check_master_health() {
    local health_response
    health_response=$(curl -s -f "$MASTER_URL/health" 2>/dev/null || echo "ERROR")
    
    if [ "$health_response" = "ERROR" ]; then
        log_error "Master is DOWN at $MASTER_URL"
        send_alert "Master node is unreachable at $MASTER_URL"
        return 1
    else
        log_success "Master is UP at $MASTER_URL"
        return 0
    fi
}

get_cluster_status() {
    local cluster_response
    cluster_response=$(curl -s -f "$MASTER_URL/cluster/nodes" 2>/dev/null || echo "{\"error\":\"Failed to fetch\"}")
    echo "$cluster_response"
}

format_bytes() {
    local bytes=$1
    if [ "$bytes" -lt 1024 ]; then
        echo "${bytes}B"
    elif [ "$bytes" -lt 1048576 ]; then
        echo "$(awk "BEGIN {printf \"%.1f\", $bytes/1024}")KB"
    elif [ "$bytes" -lt 1073741824 ]; then
        echo "$(awk "BEGIN {printf \"%.1f\", $bytes/1048576}")MB"
    else
        echo "$(awk "BEGIN {printf \"%.1f\", $bytes/1073741824}")GB"
    fi
}

display_cluster_status() {
    local status="$1"
    
    if [ "$JSON_OUTPUT" = true ]; then
        echo "$status" | jq '.'
        return
    fi
    
    # Check if jq is available
    if ! command -v jq &> /dev/null; then
        echo "$status"
        return
    fi
    
    echo ""
    echo "┌─────────────────────────────────────────────────────────────────┐"
    echo "│                  AIRClass Cluster Status                        │"
    echo "├─────────────────────────────────────────────────────────────────┤"
    
    # Parse node count
    local total_nodes
    local active_nodes
    total_nodes=$(echo "$status" | jq -r '.nodes | length' 2>/dev/null || echo "0")
    active_nodes=$(echo "$status" | jq -r '[.nodes[] | select(.status == "active")] | length' 2>/dev/null || echo "0")
    
    echo "│ Total Nodes: $total_nodes                Active: $active_nodes"
    echo "├─────────────────────────────────────────────────────────────────┤"
    
    # Display each node
    echo "$status" | jq -r '.nodes[] | 
        "│ Node: \(.node_id)\n" +
        "│   URL: \(.node_url)\n" +
        "│   Status: \(.status)\n" +
        "│   Connections: \(.current_connections)/\(.max_connections) (\(.load_percentage)%)\n" +
        "│   Last Seen: \(.last_seen)\n" +
        "├─────────────────────────────────────────────────────────────────┤"
    ' 2>/dev/null || echo "│ Error parsing node data"
    
    echo "└─────────────────────────────────────────────────────────────────┘"
    echo ""
}

analyze_health() {
    local status="$1"
    local issues=0
    
    # Check for unhealthy nodes
    local unhealthy
    unhealthy=$(echo "$status" | jq -r '[.nodes[] | select(.status != "active")] | length' 2>/dev/null || echo "0")
    
    if [ "$unhealthy" -gt 0 ]; then
        log_warning "Found $unhealthy unhealthy node(s)"
        send_alert "$unhealthy slave node(s) are unhealthy"
        ((issues++))
    fi
    
    # Check for overloaded nodes
    local overloaded
    overloaded=$(echo "$status" | jq -r '[.nodes[] | select(.load_percentage > 90)] | length' 2>/dev/null || echo "0")
    
    if [ "$overloaded" -gt 0 ]; then
        log_warning "Found $overloaded overloaded node(s) (>90% capacity)"
        send_alert "$overloaded slave node(s) are over 90% capacity"
        ((issues++))
    fi
    
    # Check for high load nodes
    local high_load
    high_load=$(echo "$status" | jq -r '[.nodes[] | select(.load_percentage > 70 and .load_percentage <= 90)] | length' 2>/dev/null || echo "0")
    
    if [ "$high_load" -gt 0 ]; then
        log_warning "Found $high_load high-load node(s) (70-90% capacity)"
    fi
    
    if [ "$issues" -eq 0 ]; then
        log_success "All nodes are healthy"
    fi
    
    return "$issues"
}

display_recommendations() {
    local status="$1"
    
    if [ "$JSON_OUTPUT" = true ]; then
        return
    fi
    
    local total_capacity
    local total_connections
    local avg_load
    
    total_capacity=$(echo "$status" | jq -r '[.nodes[].max_connections] | add' 2>/dev/null || echo "0")
    total_connections=$(echo "$status" | jq -r '[.nodes[].current_connections] | add' 2>/dev/null || echo "0")
    avg_load=$(echo "$status" | jq -r '[.nodes[].load_percentage] | add / length' 2>/dev/null || echo "0")
    
    echo "📊 Cluster Metrics:"
    echo "   Total Capacity: $total_capacity users"
    echo "   Current Load: $total_connections users"
    echo "   Average Load: $(printf "%.1f" "$avg_load")%"
    echo ""
    
    # Recommendations
    if (( $(echo "$avg_load > 80" | bc -l) )); then
        echo "⚠️  RECOMMENDATION: Scale up! Add more slave nodes."
        echo "   Command: docker-compose up -d --scale slave=N"
    elif (( $(echo "$avg_load < 30" | bc -l) )); then
        echo "💡 RECOMMENDATION: You can scale down to save resources."
        echo "   Command: docker-compose up -d --scale slave=N"
    else
        echo "✅ RECOMMENDATION: Cluster is well-balanced."
    fi
    echo ""
}

# ============================================
# Main monitoring function
# ============================================
monitor_once() {
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    if [ "$JSON_OUTPUT" = false ]; then
        echo "═══════════════════════════════════════════════════════════════"
        echo "  AIRClass Cluster Monitor - $timestamp"
        echo "═══════════════════════════════════════════════════════════════"
    fi
    
    # Check master health
    if ! check_master_health; then
        if [ "$JSON_OUTPUT" = true ]; then
            echo '{"status":"error","message":"Master unreachable"}'
        fi
        return 1
    fi
    
    # Get cluster status
    local status
    status=$(get_cluster_status)
    
    # Display status
    display_cluster_status "$status"
    
    # Analyze health
    analyze_health "$status"
    
    # Show recommendations
    display_recommendations "$status"
    
    if [ "$JSON_OUTPUT" = false ]; then
        echo "═══════════════════════════════════════════════════════════════"
    fi
}

# ============================================
# Main execution
# ============================================
if [ "$WATCH_MODE" = true ]; then
    log_info "Starting continuous monitoring (interval: ${WATCH_INTERVAL}s)"
    log_info "Press Ctrl+C to stop"
    echo ""
    
    while true; do
        monitor_once
        sleep "$WATCH_INTERVAL"
        
        # Clear screen for next iteration
        if [ "$JSON_OUTPUT" = false ]; then
            echo ""
            echo "Refreshing in ${WATCH_INTERVAL}s..."
            sleep 1
            clear
        fi
    done
else
    monitor_once
fi
