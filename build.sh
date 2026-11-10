#!/bin/bash
# Build AirType.app locally on macOS.
#
# Usage:
#   ./build.sh
#   SKIP_PIP=1 ./build.sh          # skip dependency installation
#   PYTHON=python3 ./build.sh      # use another interpreter
#   VERSION=1.2.3 ./build.sh       # override version written into Info.plist
#   ARCH=arm64 ./build.sh          # override the target architecture
#
# The script is compatible with the bash 3.2 shipped on macOS 12.

set -euo pipefail

cd "$(dirname "$0")"

PYTHON="${PYTHON:-python3.13}"
ARCH="${ARCH:-x86_64}"
MAX_MACOS="${MAX_MACOS:-12.0}"

if [ -z "${VERSION:-}" ]; then
    VERSION="$(git describe --tags --always 2>/dev/null || echo 0.0.0)"
fi
VERSION="${VERSION#v}"

if echo "$VERSION" | grep -Eq '^[0-9]+(\.[0-9]+)*$'; then
    BUNDLE_VERSION="$VERSION"
else
    echo "notice: VERSION '$VERSION' is not numeric, Info.plist falls back to 0.0.0"
    BUNDLE_VERSION="0.0.0"
fi

echo "Python:  $PYTHON ($("$PYTHON" -c 'import platform; print(platform.machine())'))"
echo "Version: $VERSION"
echo "Arch:    $ARCH"

if [ "${SKIP_PIP:-0}" != "1" ]; then
    echo "Installing dependencies..."
    "$PYTHON" -m pip install -r requirements.txt
fi

echo "Generating icons..."
"$PYTHON" src/generate_icon.py

echo "Cleaning previous build..."
rm -rf build dist AirType.spec

echo "Building with PyInstaller..."
"$PYTHON" -m PyInstaller --noconfirm --onedir --windowed --clean \
    --name "AirType" \
    --icon "icon.icns" \
    --add-data "icon.png:." \
    --osx-bundle-identifier "com.run.airtype" \
    --target-arch "$ARCH" \
    src/remote_server.py

echo "Writing bundle version..."
PLIST="dist/AirType.app/Contents/Info.plist"
/usr/libexec/PlistBuddy -c "Set :CFBundleShortVersionString $BUNDLE_VERSION" "$PLIST" 2>/dev/null \
    || /usr/libexec/PlistBuddy -c "Add :CFBundleShortVersionString string $BUNDLE_VERSION" "$PLIST"
/usr/libexec/PlistBuddy -c "Set :CFBundleVersion $BUNDLE_VERSION" "$PLIST" 2>/dev/null \
    || /usr/libexec/PlistBuddy -c "Add :CFBundleVersion string $BUNDLE_VERSION" "$PLIST"

echo "Signing (ad-hoc)..."
codesign --deep --force --verbose --sign "-" dist/AirType.app

echo "Verifying compatibility..."
./scripts/verify_bundle.sh dist/AirType.app "$ARCH" "$MAX_MACOS"

echo "Done. App is in dist/AirType.app"
