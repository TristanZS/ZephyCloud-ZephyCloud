#!/usr/bin/env sh

SCRIPT="$(readlink -f "$0")"
SCRIPT_PATH="$(dirname "$SCRIPT")"

DOMAIN=$1

if [ -z "$DOMAIN" ]; then
  echo "missing domain !!!" >&2
  exit 1
fi

REMOTE_USER="$( ssh -t "$DOMAIN" "id -un" | tr -d '[:cntrl:]' )" || exit 6
if [ -z "$REMOTE_USER" ]; then
  echo "Unable to get remote user name: $REMOTE_USER" >&2
  exit 6
fi
REMOTE_HOME=$( ssh -t "$DOMAIN" "grep '$REMOTE_USER' /etc/passwd|cut -f6 -d':'" | tr -d '[:cntrl:]' ) || exit 6
if [ -z "$REMOTE_HOME" ]; then
  echo "Unable to get remote user home" >&2
  exit 7
fi

ssh -t "$DOMAIN" "mkdir -p '$REMOTE_HOME/deploy_tmp/$DOMAIN'" || exit 6
rsync -vzrS \
    --exclude=".*" \
    --exclude="*.pyc" \
    --exclude="__pycache__" \
    --delete \
    "$SCRIPT_PATH/../../src/server/" "$DOMAIN:$REMOTE_HOME'/deploy_tmp/$DOMAIN/server/'" || exit 7
rsync -vzrS \
    --exclude=".*" \
    --exclude="*.pyc" \
    --exclude="__pycache__" \
    --delete \
    "$SCRIPT_PATH/../../db/migrations/versions/" "$DOMAIN:$REMOTE_HOME'/deploy_tmp/$DOMAIN/migrations'" || exit 7
rsync -vzrS \
    --exclude=".*" \
    --exclude="plugins/*" \
    --exclude="vendors/*" \
    --exclude="app/Config/dashboard.conf" \
    --delete \
    "$SCRIPT_PATH/../../src/dashboard/" "$DOMAIN:$REMOTE_HOME'/deploy_tmp/$DOMAIN/dashboard'" || exit 7
rsync "$SCRIPT_PATH/../../db/current_version.txt" "$DOMAIN:$REMOTE_HOME'/deploy_tmp/$DOMAIN/current_version.txt'" || exit 7
rsync "$SCRIPT_PATH/../worker_utils/ami_versions.json" "$DOMAIN:$REMOTE_HOME'/deploy_tmp/$DOMAIN/ami_versions.json'" || exit 7
rsync "$SCRIPT_PATH/updater.py" "$DOMAIN:$REMOTE_HOME'/deploy_tmp/$DOMAIN/updater.py'" || exit 7
ssh -t "$DOMAIN" 'export SYNC_FOLDER='"$REMOTE_HOME/deploy_tmp/$DOMAIN"'; \
  sudo -E -H sh -c '"'"'/usr/bin/env python '"$REMOTE_HOME/deploy_tmp/$DOMAIN/updater.py"' && \
  echo "" && \
  echo "Deployment finished !" '"'" || exit 9
