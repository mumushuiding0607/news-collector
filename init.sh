#!/bin/bash
# News Collection Project - Initialization Script
# Usage: bash init.sh

echo "=================================="
echo "News Collection Project - Init"
echo "=================================="

# Install Python dependencies
echo ""
echo "[1/3] Installing Python dependencies..."
pip install -r requirements.txt

# Install Flutter dependencies (if flutter is available)
if command -v flutter &> /dev/null; then
    echo ""
    echo "[2/3] Installing Flutter dependencies..."
    cd news_board_app
    flutter pub get
    cd ..
    echo "Flutter dependencies installed"
else
    echo ""
    echo "[2/3] Flutter not found, skipping Flutter dependencies"
fi

# Run init_db.py
echo ""
echo "[3/3] Initializing database..."
cd "新闻采集"
python init_db.py

echo ""
echo "=================================="
echo "Init complete!"
echo "=================================="
