#!/bin/sh
set -eu
curl --fail --silent --max-time 2 http://127.0.0.1:6080/vnc.html >/dev/null
xdpyinfo -display "$DISPLAY" >/dev/null 2>&1
for service in desktop window-manager vnc browser app; do
    supervisorctl -c /etc/takeoff-supervisord.conf status "$service" | grep -q RUNNING
done
