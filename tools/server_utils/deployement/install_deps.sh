#!/usr/bin/env sh

# This file aim to install API requirements
# You should not run this file locally
# This file should be run on a virtual machine, production servers and containers
# by other installation scripts

# Parameters:
API_NAME="$1"

if [ -z "$API_NAME" ]; then
    echo "You should not call this script manually. See 'make deploy' for details" >&2
    exit 1
fi

# Detect distribution
DISTRIB=$(cat /etc/os-release | grep '^ID=' | head -n1 | cut -d= -f2 | tr '[:upper:]' '[:lower:]')

if [ "$DISTRIB" = "debian" ] || [ "$DISTRIB" = "ubuntu" ]; then
    # update, install and clean cache
    export DEBIAN_FRONTEND=noninteractive
    if [ "$(stat -c '%Y' /var/lib/apt/periodic/update-success-stamp 2> /dev/null || echo 0)" -lt "$(date -d '-1 days' '+%s')" ]; then
      apt-get -y -q update
    fi
    apt-get install -y -q python-dev libpython-dev openssh-client autossh inotify-tools curl php7.0-fpm build-essential autossh || exit 4
    if [ "$2" = "DOCKER_ENV" ]; then
         curl -sSL https://get.docker.com/ | sh
    fi
    rm -rf /var/lib/apt/lists/*
elif [ "$DISTRIB" = "alpine" ]; then
    # update, install and clean cache
    apk update
    apk add --no-cache openssh-client inotify-tools autossh curl php7.0-fpm build-base py-setproctitle autossh || exit 4
    if [ "$2" = "DOCKER_ENV" ]; then
         curl -sSL https://get.docker.com/ | sh
    fi
    rm -rf /var/cache/apk/*
else
    echo "'$DISTRIB' linux distribution is not managed" >&2
    exit 3
fi

pip install --upgrade pip | cat || exit 5

pip install -I gunicorn | cat || exit 6
pip install -I flask | cat || exit 7
pip install -I boto3 | cat || exit 8
pip install -I tornado | cat || exit 9
pip install -I redis | cat || exit 10
pip install -I watchdog | cat || exit 11
pip install -I python-dateutil | cat || exit 12
pip install -I colorlog | cat || exit 13
pip install -I requests | cat || exit 14
pip install -I tblib | cat || exit 15
pip install -I psycopg2-binary | cat || exit 16
pip install -I setproctitle | cat || exit 17

# Memory inspection for debugging
pip install -I pympler | cat || exit 18
pip install -I mem_top | cat || exit 18
pip install -I objgraph | cat || exit 18
