#!/bin/sh
# Entrypoint script to handle configurable PUID/PGID

# Default to 1000:1000 if not set (common for Linux users)
PUID=${PUID:-1000}
PGID=${PGID:-1000}

# If PUID/PGID don't match current appuser, recreate the user
CURRENT_UID=$(id -u appuser 2>/dev/null || echo "999")
CURRENT_GID=$(id -g appuser 2>/dev/null || echo "999")

if [ "$PUID" != "$CURRENT_UID" ] || [ "$PGID" != "$CURRENT_GID" ]; then
    echo "Changing appuser UID:GID from $CURRENT_UID:$CURRENT_GID to $PUID:$PGID"

    # Modify group first
    if [ "$PGID" != "$CURRENT_GID" ]; then
        groupmod -o -g "$PGID" appgroup 2>/dev/null || groupadd -g "$PGID" appgroup
    fi

    # Modify user
    if [ "$PUID" != "$CURRENT_UID" ]; then
        usermod -o -u "$PUID" -g "$PGID" appuser 2>/dev/null
    fi

    # Fix ownership of app directories
    chown -R "$PUID:$PGID" /app/log /app/output 2>/dev/null || true
fi

# Ensure log and output directories exist with correct ownership
mkdir -p /app/log /app/output
chown -R "$PUID:$PGID" /app/log /app/output

# Execute the command as appuser using su
exec su -s /bin/sh -c "$*" appuser