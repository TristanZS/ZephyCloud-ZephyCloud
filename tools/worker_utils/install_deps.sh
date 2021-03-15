#!/usr/bin/env sh

# This file aim to install worker (AMI or docker) requirements
# You should not run this file locally
# This file should be run on a virtual machine, production servers and containers
# by other installation scripts
# It require the file requirements.txt to be in the same folder than this script


SCRIPT=$(readlink -f "$0")
SCRIPT_PATH=$(dirname "$SCRIPT")

# Detect distribution
DISTRIB=$(cat /etc/os-release | grep '^ID=' | head -n1 | cut -d= -f2 | tr '[:upper:]' '[:lower:]')

if [ "$DISTRIB" != "debian" ] && [ "$DISTRIB" != "ubuntu" ]; then
    echo "'$DISTRIB' linux distribution is not managed" >&2
    exit 3
fi

export DEBIAN_FRONTEND=noninteractive
if [ "$(stat -c '%Y' /var/lib/apt/periodic/update-success-stamp 2> /dev/null || echo 0)" -lt "$(date -d '-1 days' '+%s')" ]; then
  apt-get -y -q update
fi
apt-get install -y -q inxi wget gfortran coreutils sqlite3 curl || exit 4


apt-get install -y python-gdal || exit 4


TMP_DIR="$(mktemp -d)" || exit 5
test -n "$TMP_DIR" || exit 6 # Ensure TMP_DIR is not empty
wget "https://gmsh.info/bin/Linux/gmsh-4.6.0-Linux64.tgz" -O "$TMP_DIR/gmsh-4.6.0-Linux64.tgz"|| exit 7
tar -xf "$TMP_DIR/gmsh-4.6.0-Linux64.tgz" -C "$TMP_DIR" || exit 8
rm -f /usr/local/bin/gmsh4.6.0 /usr/local/bin/gmsh4 /usr/local/bin/gmsh || exit 9
mv "$TMP_DIR/gmsh-4.6.0-Linux64/bin/gmsh" /usr/local/bin/gmsh4.6.0 || exit 10
ln -s /usr/local/bin/gmsh4.6.0 /usr/local/bin/gmsh4 || exit 11
ln -s /usr/local/bin/gmsh4 /usr/local/bin/gmsh || exit 12

# We better call /usr/local/bin/gmsh4 in all our script, then remove those two lines
rm -f /usr/bin/gmsh || exit 13
ln -s /usr/local/bin/gmsh4 /usr/bin/gmsh || exit 13

rm -rf "$TMP_DIR"

pip install --upgrade pip
pip install -r "$SCRIPT_PATH/requirements.txt" | cat || exit 14
