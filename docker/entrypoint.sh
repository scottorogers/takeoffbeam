#!/bin/sh
set -eu
mkdir -p "$HOME/.config" "$HOME/.local/share" "$HOME/Documents/Takeoff Desk/Workspace" "$XDG_RUNTIME_DIR"
chmod 700 "$XDG_RUNTIME_DIR"
# CLI/MCP commands can use the same image without starting a desktop.
if [ "$#" -gt 0 ]; then
    exec "$@"
fi
exec /usr/bin/supervisord -c /etc/takeoff-supervisord.conf
