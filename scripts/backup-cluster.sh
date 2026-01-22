#!/bin/bash
# ============================================
# AIRClass Cluster Backup Script
# ============================================
# Backs up cluster configuration and state
#
# Usage:
#   ./scripts/backup-cluster.sh                    # Backup to default location
#   ./scripts/backup-cluster.sh /path/to/backup    # Custom backup location
#   ./scripts/backup-cluster.sh --auto             # Auto backup (cron friendly)

set -e

# ============================================
# Configuration
# ============================================
BACKUP_DIR="${1:-./backups}"
AUTO_MODE=false
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
BACKUP_NAME="airclass_backup_${TIMESTAMP}"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# ============================================
# Parse arguments
# ============================================
if [ "$1" = "--auto" ]; then
    AUTO_MODE=true
    BACKUP_DIR="./backups"
fi

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

# ============================================
# Create backup directory
# ============================================
mkdir -p "$BACKUP_DIR/$BACKUP_NAME"

log_info "Starting backup to: $BACKUP_DIR/$BACKUP_NAME"

# ============================================
# Backup configuration files
# ============================================
log_info "Backing up configuration files..."

# Backend config
if [ -f ".env" ]; then
    cp .env "$BACKUP_DIR/$BACKUP_NAME/.env"
    log_success "Backed up .env"
else
    log_warning ".env not found, skipping"
fi

# Docker compose files
cp docker-compose.yml "$BACKUP_DIR/$BACKUP_NAME/" 2>/dev/null || log_warning "docker-compose.yml not found"
cp docker-compose.simple.yml "$BACKUP_DIR/$BACKUP_NAME/" 2>/dev/null || log_warning "docker-compose.simple.yml not found"

# MediaMTX config
if [ -f "backend/mediamtx.yml" ]; then
    mkdir -p "$BACKUP_DIR/$BACKUP_NAME/backend"
    cp backend/mediamtx.yml "$BACKUP_DIR/$BACKUP_NAME/backend/"
    log_success "Backed up mediamtx.yml"
fi

# ============================================
# Backup cluster state (if master is running)
# ============================================
log_info "Backing up cluster state..."

MASTER_URL="${MASTER_URL:-http://localhost:8000}"
if curl -s -f "$MASTER_URL/health" > /dev/null 2>&1; then
    curl -s "$MASTER_URL/cluster/nodes" > "$BACKUP_DIR/$BACKUP_NAME/cluster_state.json" 2>/dev/null
    log_success "Backed up cluster state from $MASTER_URL"
else
    log_warning "Master not running, skipping cluster state backup"
fi

# ============================================
# Backup Docker volumes (if any)
# ============================================
log_info "Backing up Docker volumes..."

if command -v docker &> /dev/null; then
    # Check if containers are running
    if docker-compose ps | grep -q "Up"; then
        docker-compose ps > "$BACKUP_DIR/$BACKUP_NAME/docker_containers.txt"
        log_success "Backed up container status"
    fi
    
    # Backup volume list
    docker volume ls --format "{{.Name}}" | grep -i airclass > "$BACKUP_DIR/$BACKUP_NAME/docker_volumes.txt" 2>/dev/null || true
fi

# ============================================
# Create backup metadata
# ============================================
cat > "$BACKUP_DIR/$BACKUP_NAME/backup_info.txt" <<EOF
AIRClass Backup Information
============================
Backup Date: $(date)
Backup Name: $BACKUP_NAME
Hostname: $(hostname)
System: $(uname -s)

Files Included:
$(ls -lah "$BACKUP_DIR/$BACKUP_NAME" | tail -n +4)

To restore this backup:
  ./scripts/restore-cluster.sh $BACKUP_DIR/$BACKUP_NAME
EOF

log_success "Created backup metadata"

# ============================================
# Create compressed archive
# ============================================
log_info "Creating compressed archive..."

cd "$BACKUP_DIR"
tar -czf "${BACKUP_NAME}.tar.gz" "$BACKUP_NAME"
ARCHIVE_SIZE=$(du -h "${BACKUP_NAME}.tar.gz" | cut -f1)

log_success "Created archive: ${BACKUP_NAME}.tar.gz ($ARCHIVE_SIZE)"

# ============================================
# Cleanup old backups (keep last 7 days in auto mode)
# ============================================
if [ "$AUTO_MODE" = true ]; then
    log_info "Cleaning up old backups (keeping last 7 days)..."
    find "$BACKUP_DIR" -name "airclass_backup_*.tar.gz" -type f -mtime +7 -delete
    find "$BACKUP_DIR" -name "airclass_backup_*" -type d -mtime +7 -exec rm -rf {} + 2>/dev/null || true
fi

# ============================================
# Summary
# ============================================
echo ""
echo "═══════════════════════════════════════════════════════════════"
log_success "Backup completed successfully!"
echo ""
echo "  Backup location: $BACKUP_DIR/${BACKUP_NAME}.tar.gz"
echo "  Backup size: $ARCHIVE_SIZE"
echo ""
echo "To restore:"
echo "  tar -xzf $BACKUP_DIR/${BACKUP_NAME}.tar.gz"
echo "  ./scripts/restore-cluster.sh $BACKUP_DIR/$BACKUP_NAME"
echo "═══════════════════════════════════════════════════════════════"
