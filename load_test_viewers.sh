#!/bin/bash
# AIRClass Load Test - Bash version for quick testing
# Usage: ./load_test_viewers.sh [num_viewers]

NUM_VIEWERS=${1:-50}
BASE_URL="http://localhost:8000"

echo "======================================================================"
echo "🔥 AIRClass Load Test - $NUM_VIEWERS Concurrent Viewers"
echo "======================================================================"
echo "Start Time: $(date '+%Y-%m-%d %H:%M:%S')"
echo "Target: $BASE_URL"
echo "Viewers: $NUM_VIEWERS"
echo "----------------------------------------------------------------------"

START_TIME=$(date +%s)
SUCCESS_COUNT=0
FAILED_COUNT=0
TEMP_DIR=$(mktemp -d)

# Function to create a single viewer session
create_viewer() {
    local viewer_id=$1
    local response=$(curl -s -w "\n%{http_code}" -X POST \
        "$BASE_URL/api/token?user_type=student&user_id=LoadTest-Viewer-$viewer_id" 2>&1)
    
    local http_code=$(echo "$response" | tail -n1)
    local body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "200" ]; then
        echo "$body" > "$TEMP_DIR/viewer_$viewer_id.json"
        return 0
    else
        return 1
    fi
}

# Launch all viewers in parallel
echo "🚀 Launching $NUM_VIEWERS concurrent requests..."
for i in $(seq 1 $NUM_VIEWERS); do
    create_viewer $i &
done

# Wait for all background jobs to complete
wait

# Count results
for i in $(seq 1 $NUM_VIEWERS); do
    if [ -f "$TEMP_DIR/viewer_$i.json" ]; then
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    else
        FAILED_COUNT=$((FAILED_COUNT + 1))
    fi
done

END_TIME=$(date +%s)
TOTAL_ELAPSED=$((END_TIME - START_TIME))

# Print results
echo ""
echo "======================================================================"
echo "📊 Load Test Results"
echo "======================================================================"
echo "✅ Successful: $SUCCESS_COUNT"
echo "❌ Failed: $FAILED_COUNT"
echo "⏱️  Total Time: ${TOTAL_ELAPSED}s"

if [ $SUCCESS_COUNT -gt 0 ]; then
    RPS=$(echo "scale=2; $SUCCESS_COUNT / $TOTAL_ELAPSED" | bc)
    echo "🚀 Requests/Second: $RPS"
fi

echo ""
echo "----------------------------------------------------------------------"
echo "🖥️  Node Distribution:"
echo "----------------------------------------------------------------------"

# Count node distribution from responses
MAIN_COUNT=0
for i in $(seq 1 $NUM_VIEWERS); do
    if [ -f "$TEMP_DIR/viewer_$i.json" ]; then
        if grep -q ":8889" "$TEMP_DIR/viewer_$i.json"; then
            MAIN_COUNT=$((MAIN_COUNT + 1))
        fi
    fi
done

if [ $SUCCESS_COUNT -gt 0 ]; then
    MAIN_PERCENT=$(echo "scale=1; ($MAIN_COUNT / $SUCCESS_COUNT) * 100" | bc)
    BAR_LENGTH=$(echo "scale=0; $MAIN_PERCENT / 2" | bc)
    BAR=$(printf '█%.0s' $(seq 1 $BAR_LENGTH 2>/dev/null))
    printf "%-15s: %3d viewers (%5.1f%%) %s\n" "main" $MAIN_COUNT $MAIN_PERCENT "$BAR"
fi

echo ""
echo "======================================================================"
echo "End Time: $(date '+%Y-%m-%d %H:%M:%S')"
echo "======================================================================"

# Cleanup
rm -rf "$TEMP_DIR"

# Show current viewer count
echo ""
echo "📡 Checking live viewer count..."
curl -s "$BASE_URL/api/viewers" | python3 -m json.tool 2>/dev/null || curl -s "$BASE_URL/api/viewers"
