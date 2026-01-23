#!/bin/bash

# GG Archive Build Script (macOS/Linux)

set -e  # Stop on error

APP_NAME="GG_Archive"
MAIN_SCRIPT="main.py"
ICON_PATH="resources/icons/gg_icon.ico"

echo "=== GG Archive Build Start ==="

# Clean previous build
echo "Cleaning previous build files..."
rm -rf build dist *.spec

# Install PyInstaller
echo "Installing PyInstaller..."
pip install pyinstaller==6.18.0

# Run build
echo "Building..."
pyinstaller --onefile --windowed --name "$APP_NAME" \
    --add-data "resources:resources" \
    --icon "$ICON_PATH" \
    --collect-all PySide6 \
    --exclude-module tests \
    --exclude-module pytest \
    --exclude-module _pytest \
    --exclude-module unittest \
    --exclude-module test \
    "$MAIN_SCRIPT"

echo ""
echo "=== Build Complete! ==="
echo "Executable location: dist/$APP_NAME"
echo ""
echo "dist/ folder contents:"
echo "  - $APP_NAME     (executable)"
