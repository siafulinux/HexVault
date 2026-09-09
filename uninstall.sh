#!/bin/sh
set -eu

APP_NAME="HexVault"
APP_ID="hexvault"

APP_DIR="/opt/hexvault"
DESKTOP_DIR="/usr/share/applications"
PIXMAPS_DIR="/usr/share/pixmaps"

# Standard launchers
LAUNCHER="/usr/local/bin/$APP_ID"
BIN_LAUNCHER="/bin/$APP_ID"

# Legacy launchers (in case upgrading from old photorec-gui builds)
LEGACY_APP_DIR="/opt/photorec-gui"
LEGACY_LAUNCHER="/usr/local/bin/photorec-gui"
LEGACY_DESKTOP="/usr/share/applications/photorec-gui.desktop"

DESKTOP_FILE="$DESKTOP_DIR/$APP_ID.desktop"
SYSTEM_ICON="$PIXMAPS_DIR/$APP_ID.png"


usage() {
    cat <<EOF
HexVault Uninstaller

Usage:

  sudo ./uninstall.sh

Options:

  -h, --help      Show this help
EOF
}


while [ "$#" -gt 0 ]; do

    case "$1" in

        -h|--help)
            usage
            exit 0
            ;;

        *)
            echo "Unknown option: $1" >&2
            usage >&2
            exit 1
            ;;

    esac

done


# ------------------------------------------------------------
# Root check
# ------------------------------------------------------------

if [ "$(id -u)" -ne 0 ]; then

    echo
    echo "This uninstaller requires administrator privileges."
    echo
    echo "Run:"
    echo
    echo "  sudo ./uninstall.sh"
    echo

    exit 1
fi


# ------------------------------------------------------------
# Remove application
# ------------------------------------------------------------

echo
echo "Removing $APP_NAME..."
echo


# Remove launchers
for loc in "$LAUNCHER" "$BIN_LAUNCHER" "$LEGACY_LAUNCHER"; do
    if [ -e "$loc" ] || [ -L "$loc" ]; then
        echo "Removing launcher:"
        echo "  $loc"
        rm -f "$loc"
    fi
done


# Remove desktop menu entries
for desk in "$DESKTOP_FILE" "$LEGACY_DESKTOP"; do
    if [ -e "$desk" ]; then
        echo "Removing desktop entry:"
        echo "  $desk"
        rm -f "$desk"
    fi
done


# Remove pixmap icon
if [ -e "$SYSTEM_ICON" ]; then
    echo "Removing icon:"
    echo "  $SYSTEM_ICON"
    rm -f "$SYSTEM_ICON"
fi


# Remove application files
for dir in "$APP_DIR" "$LEGACY_APP_DIR"; do
    if [ -d "$dir" ]; then
        echo "Removing application directory:"
        echo "  $dir"
        rm -rf "$dir"
    fi
done


# ------------------------------------------------------------
# Refresh desktop menu database
# ------------------------------------------------------------

if command -v update-desktop-database >/dev/null 2>&1; then

    update-desktop-database \
        "$DESKTOP_DIR" \
        >/dev/null 2>&1 || true

fi


# ------------------------------------------------------------
# Finished
# ------------------------------------------------------------

echo
echo "=============================================="
echo "      HexVault successfully removed"
echo "=============================================="
echo
