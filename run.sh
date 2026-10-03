#!/usr/bin/env bash
# MediTrack ERP - Linux / macOS Launcher

set -e

echo "============================================================"
echo "  MediTrack ERP - Offline-First Medical Shop Management"
echo "============================================================"

# Ensure Python is installed
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] python3 could not be found. Please install Python 3.10+."
    exit 1
fi

# Initialize database if missing
if [ ! -f "medical_shop.db" ]; then
    echo "[INFO] First-time setup detected. Seeding baseline database..."
    python3 seed_data.py
fi

echo "[INFO] Launching MediTrack..."
python3 main.py
