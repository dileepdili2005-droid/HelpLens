#!/usr/bin/env bash
# ==============================================================================
# HelpLens - AI-Powered Everyday Problem Solver
# 1-Click Launch Script for macOS and Linux
# ==============================================================================

set -e

echo "====================================================================="
echo "          HelpLens - AI-Powered Everyday Problem Solver"
echo "====================================================================="
echo ""

# Find Python 3
if command -v python3 &>/dev/null; then
    PY_CMD="python3"
elif command -v python &>/dev/null; then
    PY_CMD="python"
else
    echo "[ERROR] Python 3 is not installed or not in PATH."
    exit 1
fi

echo "[INFO] Using Python: $($PY_CMD --version)"

# Check virtual environment
if [ ! -d "venv" ]; then
    echo "[INFO] Creating virtual environment (venv)..."
    $PY_CMD -m venv venv
fi

# Activate venv
source venv/bin/activate

echo "[1/3] Installing/verifying requirements..."
pip install -q -r requirements.txt

echo "[2/3] Checking environment configuration..."
if [ ! -f ".env" ]; then
    echo "[INFO] Copying .env.example to .env..."
    cp .env.example .env
fi

echo ""
echo "[3/3] Starting HelpLens..."
echo "====================================================================="
echo "  * HelpLens is LIVE at: http://localhost:5000"
echo "  * Press Ctrl+C to stop the server"
echo "====================================================================="
echo ""

python app.py
