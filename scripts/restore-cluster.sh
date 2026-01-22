#!/bin/bash
# ============================================
# AIRClass Cluster Restore Script
# ============================================
# Restores cluster configuration and state
#
# Usage:
#   ./scripts/restore-cluster.sh /path/to/backup
#   ./scripts/restore-cluster.sh backup.tar.gz

set -e

# ============================================
# Configuration
# ============================================
BACKUP_PATH="$1"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# ============================================
# Helper functions
# ============================================
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# ============================================
# Validate input
# ============================================
if [ -z "$BACKUP_PATH" ]; then
    log_error "Usage: $0 <backup_path>"
    echo ""
    echo "Examples:"
    echo "  $0 ./backups/airclass_backup_20240122_123456"
    echo "  $0 ./backups/airclass_backup_20240122_123456.tar.gz"
    exit 1
fi

if [ ! -e "$BACKUP_PATH" ]; then
    log_error "Backup not found: $BACKUP_PATH"
    exit 1
fi

# ============================================
# Extract archive if needed
# ============================================
RESTORE_DIR=""

if [ -f "$BACKUP_PATH" ] && [[ "$BACKUP_PATH" == *.tar.gz ]]; then
    log_info "Extracting archive: $BACKUP_PATH"
    TEMP_DIR=$(mktemp -d)
    tar -xzf "$BACKUP_PATH" -C "$TEMP_DIR"
    RESTORE_DIR="$TEMP_DIR/$(ls -1 "$TEMP_DIR" | head -1)"
    log_success "Extracted to: $RESTORE_DIR"
elif [ -d "$BACKUP_PATH" ]; then
    RESTORE_DIR="$BACKUP_PATH"
else
    log_error "Invalid backup format. Expected directory or .tar.gz file"
    exit 1
fi

# ============================================
# Display backup info
# ============================================
if [ -f "$RESTORE_DIR/backup_info.txt" ]; then
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    cat "$RESTORE_DIR/backup_info.txt"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
fi

# ============================================
# Confirmation prompt
# ============================================
read -p "This will overwrite current configuration. Continue? [y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log_warning "Restore cancelled"
    exit 0
fi

# ============================================
# Stop running services
# ============================================
log_info "Stopping running services..."

if command -v docker-compose &> /dev/null; then
    if docker-compose ps | grep -q "Up"; then
        docker-compose down
        log_success "Stopped Docker services"
    fi
fi

# Stop standalone backend if running
pkill -f "uvicorn.*main:app" 2>/dev/null || true
pkill -f mediamtx 2>/dev/null || true

# ============================================
# Restore configuration files
# ============================================
log_info "Restoring configuration files..."

# Restore .env
if [ -f "$RESTORE_DIR/.env" ]; then
    cp "$RESTORE_DIR/.env" .env
    log_success "Restored .env"
fi

# Restore docker-compose files
if [ -f "$RESTORE_DIR/docker-compose.yml" ]; then
    cp "$RESTORE_DIR/docker-compose.yml" .
    log_success "Restored docker-compose.yml"
fi

if [ -f "$RESTORE_DIR/docker-compose.simple.yml" ]; then
    cp "$RESTORE_DIR/docker-compose.simple.yml" .
    log_success "Restored docker-compose.simple.yml"
fi

# Restore MediaMTX config
if [ -f "$RESTORE_DIR/backend/mediamtx.yml" ]; then
    cp "$RESTORE_DIR/backend/mediamtx.yml" backend/
    log_success "Restored mediamtx.yml"
fi

# ============================================
# Restore cluster state (optional)
# ============================================
if [ -f "$RESTORE_DIR/cluster_state.json" ]; then
    log_info "Found cluster state backup"
    log_warning "Cluster state will be automatically rebuilt when nodes reconnect"
    # Note: We don't restore cluster state directly as it's dynamic
    # Slave nodes will re-register when they start
fi

# ============================================
# Cleanup temp files
# ============================================
if [[ "$RESTORE_DIR" == /tmp/* ]]; then
    rm -rf "$(dirname "$RESTORE_DIR")"
fi

# ============================================
# Summary
# ============================================
echo ""
echo "═══════════════════════════════════════════════════════════════"
log_success "Restore completed successfully!"
echo ""
echo "Next steps:"
echo "  1. Review configuration: cat .env"
echo "  2. Start services:"
echo "     - Standalone: ./start-dev.sh"
echo "     - Cluster: docker-compose up -d"
echo "  3. Verify status:"
echo "     - Health: curl http://localhost:8000/health"
echo "     - Cluster: curl http://localhost:8000/cluster/nodes"
echo "═══════════════════════════════════════════════════════════════"
