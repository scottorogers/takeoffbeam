#!/bin/sh
set -eu
attempt=0
until xdpyinfo -display "$DISPLAY" >/dev/null 2>&1; do
    attempt=$((attempt + 1))
    if [ "$attempt" -ge 100 ]; then
        echo "Virtual display did not start" >&2
        exit 1
    fi
    sleep 0.1
done
exec "$@"
