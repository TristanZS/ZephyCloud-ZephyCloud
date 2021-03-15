#!/usr/bin/env sh

# Configure a worker AMI image on EC2 and install software requirements
# It should be copied on the Instance before being run
# You should not use this script directly: see `make worker_ami`
#
# This script will
# * setup locale
# * configure admin access
# * install required software (openfoam, etc...)
# * configure ssh access


# Constants and system detection
ZS_EMAIL=sysadmin@aziugo.com
WORKER_HOSTNAME="worker"

SCRIPT=$(readlink -f "$0")
SCRIPT_PATH=$(dirname "$SCRIPT")
APP_PATH=$(realpath "$SCRIPT_PATH/../..")

API_NAME=$1

# ------------------------------- Detect and prepare distribution -------------------------

DISTRIB=$(cat /etc/os-release | grep '^ID=' | head -n1 | cut -d= -f2 | tr '[:upper:]' '[:lower:]')

# Check distribution
if [ "$DISTRIB" != "debian" ] && [ "$DISTRIB" != "ubuntu" ]; then
    echo "This installer only manage debian or ubuntu distribution, not '$DISTRIB'"
    exit 2
fi

REQUIRED_LOCALE="en_US.UTF-8"
NEED_REGEN_LOCALES=0
for locale_var in REQUIRED_LOCALE LC_ALL LC_NAME LC_NUMERIC; do
    locale_val=$(eval echo \$$locale_var)
    if [ -z "$locale_val" ]; then
		locale_val="$REQUIRED_LOCALE"
		eval export $locale_var=$locale_val
    fi
	locale_min=$(echo "$locale_val" | tr '[:upper:]' '[:lower:]')
	if ! locale -a | tr '[:upper:]' '[:lower:]' | grep -qE "^$locale_val\$"; then
		NEED_REGEN_LOCALES=1
		sed -i 's/ *# *'"$locale_val/$locale_val/" /etc/locale.gen
	fi
done
if [ "$NEED_REGEN_LOCALES" -eq 1 ]; then
	locale-gen
fi

echo "COUCOU"
# Manage clean timezone
ln -sf /usr/share/zoneinfo/Etc/UTC /etc/localtime
echo "Etc/UTC" > /etc/timezone
dpkg-reconfigure --frontend=noninteractive tzdata 2>&1

# ------------------------------- Set Hostname -------------------------
echo "COUCOU2"
if which hostnamectl >/dev/null 2>&1; then
    hostnamectl set-hostname "$WORKER_HOSTNAME"
fi
echo "$WORKER_HOSTNAME" > /etc/hosts
cat /etc/hosts | grep -E '^127.0.0.1'
cp -af /etc/hosts /etc/hosts.bkp
cat /etc/hosts | sed 's/'"$WORKER_HOSTNAME"'//' | sed -E 's/^127\.0\.0\.1(.*)/127.0.0.1\1 '"$WORKER_HOSTNAME"'/' > /tmp/hosts.tmp
cp /tmp/hosts.tmp /etc/hosts
chmod 644 /etc/hosts
echo "COUCOU3"
# --------------------------------Disable auto update ----------------------------

systemctl stop apt-daily.timer
systemctl disable apt-daily.timer

start_time="$(date -u +%s)"
if lsof /var/lib/dpkg/lock > /dev/null 2>&1 || lsof /var/lib/dpkg/lock-frontend > /dev/null 2>&1; then
  echo "waiting for auto-update to stop..."
  while lsof /var/lib/dpkg/lock > /dev/null 2>&1 || lsof /var/lib/dpkg/lock-frontend > /dev/null 2>&1; do
    now="$(date -u +%s)"
    elapsed="$(($now-$start_time))"
    if [ "$elapsed" -gt 900 ] ; then
      echo "We were waiting for dpkg to be ready for more than 5 minutes" >&2
      lsof /var/lib/dpkg/lock >&2
      lsof /var/lib/dpkg/lock-frontend >&2
      exit 2
    fi
    sleep 1
  done
fi

# ------------------------------- Admin key installation -------------------------

DEFAULT_PASSWORD=$(cat "$SCRIPT_PATH/default_password.txt" | head -n1)
for file in $(ls -1 "$SCRIPT_PATH/admin_keys"); do
    user_name=$(echo "$file" | sed -r 's/\.pub$//')
    if ! grep -qE "^${user_name}:" /etc/passwd; then
        useradd "$user_name" -m -s /bin/bash || exit 6
        echo "$user_name:$DEFAULT_PASSWORD" | chpasswd || exit 6
    fi
    if ! groups "$user_name" | grep -q '\sudo\b'; then
        usermod -a -G sudo "$user_name" || exit 6
    fi
    homedir=$( getent passwd "$user_name" | cut -d: -f6 )
    mkdir -p "$homedir/.ssh"
    cat "$SCRIPT_PATH/admin_keys/$file" > "$homedir/.ssh/authorized_keys"  || exit 7
    echo "" >> "$homedir/.ssh/authorized_keys"
    chmod 600 "$homedir/.ssh/authorized_keys"
    chmod 700 "$homedir/.ssh"
    chown -R "$user_name:$user_name" "$homedir/.ssh"
done

if [ -e /etc/sudoers.d ]; then
  rm -rf /etc/sudoers.d/60-sudo-group
  echo "%sudo ALL=(ALL:ALL) ALL" > /etc/sudoers.d/60-sudo-group
else
  sed -iE '/^%sudo/d' /etc/sudoers
  echo "%sudo ALL=(ALL:ALL) ALL" >> /etc/sudoers
fi



# ------------------------------- API key installation -------------------------

adduser --shell "/bin/bash" --disabled-password --gecos "" "aziugo"
homedir=$( getent passwd "aziugo" | cut -d: -f6 )
mkdir -p "$homedir/.ssh"
cat "$SCRIPT_PATH/api_keys" >> "$homedir/.ssh/authorized_keys"
echo "" >> "$homedir/.ssh/authorized_keys"
chmod 600 "$homedir/.ssh/authorized_keys"
chmod 700 "$homedir/.ssh"
chown -R "aziugo:aziugo" "$homedir/.ssh"
mkdir -p "/root/.ssh"
cat "$SCRIPT_PATH/root_api_keys" >> "/root/.ssh/authorized_keys"
echo "" >> "/root/.ssh/authorized_keys"
chmod 600 "/root/.ssh/authorized_keys"
chmod 700 "/root/.ssh"
chown -R "root:root" "/root/.ssh"

# ------------------------------- Install requirements -------------------------

# Installing requirements
echo "Installing dependencies..."
# APT
export DEBIAN_FRONTEND=noninteractive
sh -c "wget -q -O - http://dl.openfoam.org/gpg.key | apt-key add -"
add-apt-repository http://dl.openfoam.org/ubuntu
apt-get -y -q update

# For china, if connection is really bad
# sleep 60

start_time="$(date -u +%s)"
if lsof /var/lib/dpkg/lock > /dev/null 2>&1 || lsof /var/lib/dpkg/lock-frontend > /dev/null 2>&1; then
  echo "waiting for auto-update to stop..."
  while lsof /var/lib/dpkg/lock > /dev/null 2>&1 || lsof /var/lib/dpkg/lock-frontend > /dev/null 2>&1; do
    now="$(date -u +%s)"
    elapsed="$(($now-$start_time))"
    if [ "$elapsed" -gt 900 ] ; then
      echo "We were waiting for dpkg to be ready for more than 5 minutes" >&2
      lsof /var/lib/dpkg/lock >&2
      lsof /var/lib/dpkg/lock-frontend >&2
      exit 2
    fi
    sleep 1
  done
fi

apt-get -y upgrade || exit 3


# General server install
apt-get -y install vim iotop htop rsync build-essential software-properties-common wget curl || exit 3
apt-get -y install openssh-server openssh-client rng-tools nfs-kernel-server nfs-common sudo || exit 3
snap install yq

# We try 5 times because often the openfoam repository fail
for i in 1 2 3 4; do
  apt-get -y install openfoam8 && break || sleep 300
done
apt-get -y install openfoam8 || exit 3

echo "source /opt/openfoam8/etc/bashrc" >> /home/aziugo/.bashrc
echo "source /opt/openfoam8/etc/bashrc" >> /home/aziugo/.bash_profile

# Install python
apt-get -y install python python-dev python-pip python-cryptography libssl-dev python-virtualenv || exit 3
HOME="/root" pip install --upgrade pip | cat || exit 4

# virtualenv "$homedir/aziugo_env" || exit 6
# . "$homedir/aziugo_env/bin/activate" || exit 7

apt-get -y -q update
apt-get install binfmt-support || exit 8

# ------------------------------- API specific requirements -------------------------

"$SCRIPT_PATH/install_deps.sh" "$API_NAME" || { echo "specific installation failed with exit code $?" >&2 && exit 10; }

# ------------------------------- END API specific requirements ---------------------



# ------------------------------- Configure system ---------------------------------

echo "Configuring rng-tools"
sed -iR "/^HRNGDEVICE/d" /etc/default/rng-tools
echo "HRNGDEVICE=/dev/urandom" >> /etc/default/rng-tools
if which systemctl >/dev/null 2>&1; then
    systemctl enable rng-tools.service
    systemctl restart rng-tools.service
elif which service >/dev/null 2>&1; then
    service rng-tools restart
fi
echo "done."
echo ""

echo "Configuring ssh server"
# More ssh security
sed -i '/PasswordAuthentication/d' /etc/ssh/sshd_config
sed -i '/AuthorizedKeysFile/d' /etc/ssh/sshd_config
sed -i '/PermitUserEnvironment/d' /etc/ssh/sshd_config
sed -i '/PermitRootLogin/d' /etc/ssh/sshd_config
sed -i '/PubkeyAuthentication/d' /etc/ssh/sshd_config
echo "PasswordAuthentication no" >> /etc/ssh/sshd_config
echo "AuthorizedKeysFile .ssh/authorized_keys" >> /etc/ssh/sshd_config
echo "PermitUserEnvironment yes" >> /etc/ssh/sshd_config
echo "PermitRootLogin prohibit-password" >> /etc/ssh/sshd_config
sed -i -r '/AcceptEnv/s/(LANG|LC_[^ ]+) *//g' /etc/ssh/sshd_config
sed -i 's/AcceptEnv *$//' /etc/ssh/sshd_config
# More secure version: echo "PermitRootLogin no" >> /etc/ssh/sshd_config
echo "PubkeyAuthentication yes" >> /etc/ssh/sshd_config
echo "done"
echo ""

# ------------------------------- Install ping checker -------------------------

mv "$SCRIPT_PATH/ping_check.py" "/usr/local/bin" || exit 11
chmod +x "/usr/local/bin/ping_check.py"
mv "$SCRIPT_PATH/ping_check.service" "/etc/systemd/system" || exit 11
systemctl daemon-reload || exit 12
systemctl enable ping_check.service || exit 12

# ------------------------------- Do toolchain compilation -------------------------

python "$SCRIPT_PATH/toolchain_compiler.py" "$SCRIPT_PATH/worker_scripts/toolchain_to_compile/to_compile.json" "$SCRIPT_PATH/worker_scripts/toolchain" || exit 21
rm -rf "$SCRIPT_PATH/worker_scripts/toolchain_to_compile" || exit 22
rm -rf "$SCRIPT_PATH/toolchain_compiler.py" || exit 23

# ------------------------------- Install main files -------------------------

cp -a "$SCRIPT_PATH/worker_scripts" "$homedir/worker_scripts" || exit 24
chown -R "aziugo:aziugo" "$homedir" || exit 25
chmod a+rx "$homedir/worker_scripts/python_venv.sh" || exit 26



# -------------------------------- Allow user to shutdown the worker ---------

if [ -e /etc/sudoers.d ]; then
  rm -rf /etc/sudoers.d/70-aziugo
  echo "aziugo ALL=NOPASSWD: /usr/bin/systemctl poweroff" > /etc/sudoers.d/70-aziugo
  echo "aziugo ALL=NOPASSWD: /usr/bin/systemctl halt" >> /etc/sudoers.d/70-aziugo
  echo "aziugo ALL=NOPASSWD: /usr/bin/systemctl reboot" >> /etc/sudoers.d/70-aziugo
else
  sed -iE '/^aziugo /d' /etc/sudoers
  echo "aziugo ALL=NOPASSWD: /usr/bin/systemctl poweroff" >> /etc/sudoers
  echo "aziugo ALL=NOPASSWD: /usr/bin/systemctl halt" >> /etc/sudoers
  echo "aziugo ALL=NOPASSWD: /usr/bin/systemctl reboot" >> /etc/sudoers
fi

sync

exit 0
