#!/usr/bin/env sh

SCRIPT=$(readlink -f "$0")
SCRIPT_PATH=$(dirname "$SCRIPT")
CURRENT_VIRT_ENV_PATH="$SCRIPT_PATH/aziugo_env"
USER_VIRT_ENV_PATH="$HOME/aziugo_env"

if [ -e "$CURRENT_VIRT_ENV_PATH" ]; then
  . "$CURRENT_VIRT_ENV_PATH/bin/activate" || exit 1
  $("$@")
  RESULT_CODE="$?"
  deactivate
  exit "$RESULT_CODE"
elif [ -e "$USER_VIRT_ENV_PATH" ]; then
  . "$USER_VIRT_ENV_PATH/bin/activate" || exit 1
  $("$@")
  RESULT_CODE="$?"
  deactivate
  exit "$RESULT_CODE"
else
  exec python "$@"
fi
