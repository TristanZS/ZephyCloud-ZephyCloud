#!/usr/bin/env sh

SCRIPT="$(readlink -f "$0")"
SCRIPT_PATH="$(dirname "$SCRIPT")"

exec /usr/bin/env sh "$SCRIPT_PATH/server_utils/any_sync.sh" "apidev.zephy-science.com"
