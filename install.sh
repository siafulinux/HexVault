#!/bin/sh
set -eu

APP_NAME="HexVault"
APP_ID="hexvault"
SCRIPT_NAME="hexvault.py"

# Standard location for locally installed software.
BIN_DIR="/usr/local/bin"
APP_DIR="/opt/hexvault"
DESKTOP_DIR="/usr/share/applications"
PIXMAPS_DIR="/usr/share/pixmaps"

usage() {
    cat <<EOF
HexVault Installer

Usage:
  sudo ./install.sh [options]

Options:
  --bin-dir DIR   Install launcher into DIR
                  Default: /usr/local/bin

  --app-dir DIR   Install application into DIR
                  Default: /opt/hexvault

  --uninstall     Remove HexVault

  -h, --help      Show this help

Examples:

  sudo ./install.sh

  sudo ./install.sh --bin-dir /bin

  sudo ./install.sh --uninstall
EOF
}

UNINSTALL=0

while [ "$#" -gt 0 ]; do
    case "$1" in
        --bin-dir)
            if [ "$#" -lt 2 ]; then
                echo "Error: --bin-dir requires a directory." >&2
                exit 1
            fi
            BIN_DIR="$2"
            shift 2
            ;;

        --app-dir)
            if [ "$#" -lt 2 ]; then
                echo "Error: --app-dir requires a directory." >&2
                exit 1
            fi
            APP_DIR="$2"
            shift 2
            ;;

        --uninstall)
            UNINSTALL=1
            shift
            ;;

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
    echo "This installer requires administrator privileges."
    echo
    echo "Run:"
    echo
    echo "  sudo ./install.sh"
    echo
    exit 1
fi


# ------------------------------------------------------------
# Paths
# ------------------------------------------------------------

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

SOURCE_SCRIPT="$SCRIPT_DIR/$SCRIPT_NAME"
LAUNCHER="$BIN_DIR/$APP_ID"
DESKTOP_FILE="$DESKTOP_DIR/$APP_ID.desktop"
SYSTEM_ICON="$PIXMAPS_DIR/$APP_ID.png"


# ------------------------------------------------------------
# Uninstall
# ------------------------------------------------------------

if [ "$UNINSTALL" -eq 1 ]; then

    echo
    echo "Removing $APP_NAME..."
    echo

    rm -f "$LAUNCHER"
    rm -f "$DESKTOP_FILE"
    rm -f "$SYSTEM_ICON"
    rm -rf "$APP_DIR"

    if command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database "$DESKTOP_DIR" >/dev/null 2>&1 || true
    fi

    echo "$APP_NAME has been removed."
    echo

    exit 0
fi


# ------------------------------------------------------------
# Verify source files
# ------------------------------------------------------------

if [ ! -f "$SOURCE_SCRIPT" ]; then
    echo "Error: $SCRIPT_NAME was not found." >&2
    echo >&2
    echo "The following files should be together:" >&2
    echo >&2
    echo "  install.sh" >&2
    echo "  $SCRIPT_NAME" >&2
    echo >&2
    exit 1
fi


# ------------------------------------------------------------
# Find Python 3 + Tkinter
# ------------------------------------------------------------

PYTHON=""

for candidate in python3 python; do

    if command -v "$candidate" >/dev/null 2>&1; then

        if "$candidate" -c 'import tkinter' >/dev/null 2>&1; then
            PYTHON=$(command -v "$candidate")
            break
        fi

    fi

done


if [ -z "$PYTHON" ]; then

    echo "Error: Python 3 with Tkinter is required." >&2
    echo >&2
    echo "On Debian / Ubuntu / Linux Mint, install it with:" >&2
    echo >&2
    echo "  sudo apt install python3 python3-tk python3-pil python3-pil.imagetk" >&2
    echo >&2

    exit 1
fi


echo
echo "Python detected:"
echo "  $PYTHON"
echo


# ------------------------------------------------------------
# Create application directory
# ------------------------------------------------------------

echo "Installing application to:"
echo "  $APP_DIR"
echo

install -d -m 0755 "$APP_DIR"


# ------------------------------------------------------------
# Install Python application & Assets
# ------------------------------------------------------------

install -m 0644 \
    "$SOURCE_SCRIPT" \
    "$APP_DIR/$SCRIPT_NAME"

if [ -d "$SCRIPT_DIR/assets" ]; then
    echo "Installing assets..."
    install -d -m 0755 "$APP_DIR/assets"
    cp -r "$SCRIPT_DIR/assets/"* "$APP_DIR/assets/"
    chmod -R 0644 "$APP_DIR/assets/"*
fi

# Copy icon to pixmaps directory for system launcher support
if [ -f "$SCRIPT_DIR/assets/icon.png" ]; then
    install -d -m 0755 "$PIXMAPS_DIR"
    install -m 0644 "$SCRIPT_DIR/assets/icon.png" "$SYSTEM_ICON"
fi


# ------------------------------------------------------------
# Compile check
# ------------------------------------------------------------

echo "Checking Python application..."

if ! "$PYTHON" -m py_compile "$APP_DIR/$SCRIPT_NAME"; then

    echo
    echo "Error: Python compile check failed." >&2
    echo "Installation aborted." >&2

    rm -rf "$APP_DIR"
    rm -f "$SYSTEM_ICON"

    exit 1
fi


# Remove __pycache__ created by compile check.
rm -rf "$APP_DIR/__pycache__"


# ------------------------------------------------------------
# Create launcher
# ------------------------------------------------------------

echo "Installing launcher:"
echo "  $LAUNCHER"
echo

install -d -m 0755 "$BIN_DIR"


cat > "$LAUNCHER" <<EOF
#!/bin/sh

exec "$PYTHON" "$APP_DIR/$SCRIPT_NAME" "\$@"
EOF


chmod 0755 "$LAUNCHER"


# ------------------------------------------------------------
# Create desktop menu entry
# ------------------------------------------------------------

echo "Installing desktop menu entry:"
echo "  $DESKTOP_FILE"
echo

install -d -m 0755 "$DESKTOP_DIR"

ICON_NAME="drive-harddisk"
if [ -f "$SYSTEM_ICON" ]; then
    ICON_NAME="$APP_ID"
fi

cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=$APP_NAME
GenericName=Digital File Recovery
Comment=Deleted file recovery tool powered by PhotoRec
Exec=$LAUNCHER
Icon=$ICON_NAME
Terminal=false
Categories=System;Utility;Security;
Keywords=HexVault;PhotoRec;file recovery;data recovery;deleted files;forensics;carving;
StartupNotify=true
EOF


chmod 0644 "$DESKTOP_FILE"


# ------------------------------------------------------------
# Update desktop application database
# ------------------------------------------------------------

if command -v update-desktop-database >/dev/null 2>&1; then

    update-desktop-database \
        "$DESKTOP_DIR" \
        >/dev/null 2>&1 || true

fi


# ------------------------------------------------------------
# Installation complete
# ------------------------------------------------------------

echo
echo "=============================================="
echo "          HexVault Installed Successfully"
echo "=============================================="
echo
echo "Application:"
echo "  $APP_DIR/$SCRIPT_NAME"
echo
echo "Launcher:"
echo "  $LAUNCHER"
echo
echo "Desktop entry:"
echo "  $DESKTOP_FILE"
echo
echo "You can now launch HexVault from your desktop"
echo "application menu."
echo
echo "Or run from a terminal:"
echo
echo "  $APP_ID"
echo
echo "To uninstall:"
echo
echo "  sudo ./uninstall.sh"
echo
