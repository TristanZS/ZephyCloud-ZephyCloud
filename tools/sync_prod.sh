#!/usr/bin/env sh

SCRIPT="$(readlink -f "$0")"
SCRIPT_PATH="$(dirname "$SCRIPT")"


read -r -p "Are you sure to overwrite ZephyCloud production? [y/N] " response
case "$response" in
    [yY][eE][sS]|[yY])
        exec /usr/bin/env sh "$SCRIPT_PATH/server_utils/any_sync.sh" "api.zephycloud.aziugo.com"
        ;;
    *)
        exit 0
        ;;
esac
