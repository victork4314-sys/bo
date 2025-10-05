#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

python -m compileall core cli gui
python cli/biospeak_cli.py verify

./build_web.sh

OS_NAME="$(uname)"

if [[ "$OS_NAME" == "Darwin" ]]; then
  BUILD_DIR="build/macos"
  DIST_DIR="dist"
  PAYLOAD="$BUILD_DIR/payload"
  rm -rf "$BUILD_DIR"
  mkdir -p "$BUILD_DIR/pyi" "$BUILD_DIR/build"

  pyinstaller --noconfirm --clean --onefile cli/biospeak_cli.py --name biospeak --distpath "$BUILD_DIR/pyi" --workpath "$BUILD_DIR/build"
  pyinstaller --noconfirm --clean gui/biospeak_studio.py --name BioSpeakStudio --windowed --distpath "$BUILD_DIR/pyi" --workpath "$BUILD_DIR/build" --add-data "core:core" --add-data "web:web"
  pyinstaller --noconfirm --clean installer/welcome_launcher.py --name BioSpeakWelcome --onefile --windowed --distpath "$BUILD_DIR/pyi" --workpath "$BUILD_DIR/build"

  mkdir -p "$PAYLOAD"/{browser,desktop,terminal,launcher,core,examples}
  cp "$BUILD_DIR/pyi/biospeak" "$PAYLOAD/terminal/biospeak"
  cp -R "$BUILD_DIR/pyi/BioSpeakStudio.app" "$PAYLOAD/desktop/"
  cp "$BUILD_DIR/pyi/BioSpeakWelcome" "$PAYLOAD/launcher/BioSpeakWelcome"
  cp -R dist/. "$PAYLOAD/browser"
  cp -R core/. "$PAYLOAD/core"
  cp -R examples/. "$PAYLOAD/examples"
  cp README.md "$PAYLOAD"

  pyinstaller --noconfirm --clean installer/setup_wizard.py --name BioSpeakInstaller --windowed --distpath "$BUILD_DIR/pyi" --workpath "$BUILD_DIR/build" --add-data "$PAYLOAD:payload"

  DMG_ROOT="$BUILD_DIR/dmg_root"
  rm -rf "$DMG_ROOT"
  mkdir -p "$DMG_ROOT"
  cp -R "$BUILD_DIR/pyi/BioSpeakInstaller.app" "$DMG_ROOT/"
  mkdir -p "$DMG_ROOT/.background"
  cp installer/icons/biospeak.svg "$DMG_ROOT/.background/biospeak.svg"

  create-dmg \
    --volname "Bio Speak Installer" \
    --volicon installer/icons/biospeak.svg \
    --window-size 600 400 \
    --icon-size 128 \
    --app-drop-link 440 200 \
    "$DIST_DIR/BioSpeakInstaller.dmg" \
    "$DMG_ROOT"

  echo "Build complete -- macOS installer written to dist/BioSpeakInstaller.dmg"
  exit 0
fi

if [[ "$OS_NAME" == "Linux" ]]; then
  BUILD_DIR="build/linux"
  DIST_DIR="dist"
  PAYLOAD="$BUILD_DIR/payload"
  rm -rf "$BUILD_DIR"
  mkdir -p "$BUILD_DIR/pyi" "$BUILD_DIR/build"

  pyinstaller --noconfirm --clean --onefile cli/biospeak_cli.py --name biospeak --distpath "$BUILD_DIR/pyi" --workpath "$BUILD_DIR/build"
  pyinstaller --noconfirm --clean --onefile --windowed gui/biospeak_studio.py --name BioSpeakStudio --distpath "$BUILD_DIR/pyi" --workpath "$BUILD_DIR/build" --add-data "core:core" --add-data "web:web"
  pyinstaller --noconfirm --clean --onefile --windowed installer/welcome_launcher.py --name BioSpeakWelcome --distpath "$BUILD_DIR/pyi" --workpath "$BUILD_DIR/build"

  mkdir -p "$PAYLOAD"/{browser,desktop,terminal,launcher,core,examples}
  cp "$BUILD_DIR/pyi/biospeak" "$PAYLOAD/terminal/biospeak"
  cp "$BUILD_DIR/pyi/BioSpeakStudio" "$PAYLOAD/desktop/BioSpeakStudio"
  cp "$BUILD_DIR/pyi/BioSpeakWelcome" "$PAYLOAD/launcher/BioSpeakWelcome"
  cp -R dist/. "$PAYLOAD/browser"
  cp -R core/. "$PAYLOAD/core"
  cp -R examples/. "$PAYLOAD/examples"
  cp README.md "$PAYLOAD"

  pyinstaller --noconfirm --clean --onefile --windowed installer/setup_wizard.py --name BioSpeakInstaller --distpath "$BUILD_DIR/pyi" --workpath "$BUILD_DIR/build" --add-data "$PAYLOAD:payload"

  APPDIR="$BUILD_DIR/AppDir"
  rm -rf "$APPDIR"
  mkdir -p "$APPDIR/usr/bin" "$APPDIR/usr/share/applications" "$APPDIR/usr/share/icons/hicolor/scalable/apps"
  cp "$BUILD_DIR/pyi/BioSpeakInstaller" "$APPDIR/usr/bin/BioSpeakInstaller"
  cp installer/appimage/AppRun "$APPDIR/AppRun"
  chmod +x "$APPDIR/AppRun" "$APPDIR/usr/bin/BioSpeakInstaller"
  cp installer/appimage/BioSpeak.desktop "$APPDIR/usr/share/applications/BioSpeak.desktop"
  cp installer/icons/biospeak.svg "$APPDIR/usr/share/icons/hicolor/scalable/apps/biospeak.svg"

  (cd "$APPDIR" && find . -name '*.pyc' -delete)
  appimagetool "$APPDIR" "$DIST_DIR/BioSpeakInstaller.AppImage"

  echo "Build complete -- Linux installer written to dist/BioSpeakInstaller.AppImage"
  exit 0
fi

echo "Unsupported platform: $OS_NAME" >&2
exit 1
