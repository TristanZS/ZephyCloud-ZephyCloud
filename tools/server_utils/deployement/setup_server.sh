#!/usr/bin/env sh

# Configure a server and install software requirements
# It should be installed on the server before being run
# You should not use this script directly: see `make deploy`
#
# This script will
# * setup locale
# * configure admin access
# * install required software (nginx, python, redis, etc...)
# * call tools/server_utils/install_deps.sh to install api specific libraries and software
# * configure services

# ------------------------------- Compute vars and consts -------------------------

usage() {
  echo "Usage: setup_server.sh [options] API_NAME SERVER_NAME"
  echo ""
  echo "Options:"
  echo "  --conf, -c CONF_PATH      The path to the configuration folder"
  echo "  --dashboard, -d           Deploy the dashboard"
  echo "  --api,                    Deploy the api"
  echo "  --db                      Deploy the database"
  echo "  --restart, -r             Restart the services"
  echo "  --help, -h                Display this help message"
}

CONF_PATH=""
DEPLOY_CONF=0
DEPLOY_DASHBOARD=0
DEPLOY_API=0
DEPLOY_DB=0
RESTART=0

for arg in "$@"; do
  if [ "$arg" = "-h" ] || [ "$arg" = "--help" ]; then
    usage
    exit 0
  fi
done

while [ "$#" -gt 2 ]; do
  case "$1" in
    --)
      shift
      break
      ;;

    -c|--conf)
      shift
      CONF_PATH="$1"
      DEPLOY_CONF=1
      if [ -z "$CONF_PATH" ] || [ ! -d "$CONF_PATH" ] ; then
        echo "Bad config folder" >&2
        exit 1
      fi
      shift
      ;;

    -d|--dashboard)
      shift
      DEPLOY_DASHBOARD=1
      ;;

    --api)
      shift
      DEPLOY_API=1
      ;;

    --db)
      shift
      DEPLOY_DB=1
      ;;

    -r|--restart)
      shift
      RESTART=1
      ;;

    *)
      echo "Unknown parameter $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [ "$#" -ne 2 ]; then
  echo "Bad parameters" >&2
  usage
  exit 1
fi

# Parameters:
API_NAME="$1"
SERVER_NAME="$2"


# Constants and system detection
DEST_PATH="/home/$API_NAME"
APP_USER="$API_NAME"
ZS_EMAIL=sysadmin@aziugo.com

SCRIPT=$(readlink -f "$0")
SCRIPT_PATH=$(dirname "$SCRIPT")
INSTALL_PATH=$(realpath "$SCRIPT_PATH/../..")
INSTALL_FILES="$INSTALL_PATH/tools/install/install_files"
DB_PATH="/home/${API_NAME}/database"
MIGRATIONS_PATH="$DB_PATH/migrations"

MAIN_SERVICE="${API_NAME}"
SERVICE_LIST="${API_NAME} ${API_NAME}_webapi ${API_NAME}_websocket ${API_NAME}_files"
STOPPABLE_SERVICE_LIST="${API_NAME}_webapi ${API_NAME}_websocket"


get_ini_val() {
  # Read a ini file and get a specific value
  ini_file="$1"
  section="$2"
  key="$3"

  section_info=$(cat "$ini_file" | sed -nr -e '/^\['"$section"'\]/,/^\[/{/^\[/d;p;}')
  value=$(echo "$section_info" | awk -F "=" '/'"$key"'/ {print $2}')
  echo "$value"
}


run_pg() {
  # Execute postgres command
  sql_command="$1"
  sql_command_db="$2"
  if [ -z "$sql_command_db" ]; then
    sql_command_db="postgres"
  fi

  tmpfile=$(mktemp /tmp/run_pg.XXXXXX)
  echo "$1;" > "$tmpfile"

  su -l postgres -c "psql postgres -d '$sql_command_db' -tA" < "$tmpfile"
  result="$?"
  rm -f "$tmpfile"
  return "$result"
}

# Checking for previous install if no config is provided
if [ "$DEPLOY_CONF" -eq 0 ]; then
  if [ ! -f "$DEST_PATH/config.conf" ]; then
      echo "This server seems to don't have prior $API_NAME installation" >&2
      echo "You must provide a configuration for the first installation" >&2
      exit 2
  fi
fi

# Deploy configuration
if [ "$DEPLOY_CONF" -eq 1 ]; then
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

  # Manage clean timezone
  ln -sf /usr/share/zoneinfo/Etc/UTC /etc/localtime
  echo "Etc/UTC" > /etc/timezone
  dpkg-reconfigure --frontend=noninteractive tzdata 2>&1


  # ------------------------------- Manage users -------------------------

  #manage user and path
  echo "creating user $APP_USER..."

  if ! grep -q "^$APP_USER:" /etc/passwd ; then
    useradd --home "$DEST_PATH" "$APP_USER" || exit 12
  fi
  mkdir -p "$DEST_PATH"
  chown "$APP_USER:$APP_USER" "$DEST_PATH"

  DEFAULT_PASSWORD=$(cat "$CONF_PATH/default_password.txt" | head -n1)
  rm -f "$CONF_PATH/default_password.txt"

  for file in $(ls -1 "$CONF_PATH/admin_keys"); do
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
    cat "$CONF_PATH/admin_keys/$file" > "$homedir/.ssh/authorized_keys"  || exit 7
    echo "" >> "$homedir/.ssh/authorized_keys"
    chmod 600 "$homedir/.ssh/authorized_keys"
    chmod 700 "$homedir/.ssh"
    chown -R "$user_name:$user_name" "$homedir/.ssh"
  done

  # More ssh security
  sed -i '/PasswordAuthentication/d' /etc/ssh/sshd_config
  sed -i '/AuthorizedKeysFile/d' /etc/ssh/sshd_config
  sed -i '/PermitRootLogin/d' /etc/ssh/sshd_config
  sed -i '/PubkeyAuthentication/d' /etc/ssh/sshd_config
  echo "PasswordAuthentication no" >> /etc/ssh/sshd_config
  echo "AuthorizedKeysFile .ssh/authorized_keys" >> /etc/ssh/sshd_config
  echo "PermitRootLogin prohibit-password" >> /etc/ssh/sshd_config
  sed -i -r '/AcceptEnv/s/(LANG|LC_[^ ]+) *//g' /etc/ssh/sshd_config
  sed -i 's/AcceptEnv *$//' /etc/ssh/sshd_config
  # More secure version: echo "PermitRootLogin no" >> /etc/ssh/sshd_config
  echo "PubkeyAuthentication yes" >> /etc/ssh/sshd_config

  echo "done"
  echo ""

  # ------------------------------- Install requirements -------------------------

  # Installing requirements
  echo "Installing dependencies..."

  # APT
  export DEBIAN_FRONTEND=noninteractive
  wget -q https://www.postgresql.org/media/keys/ACCC4CF8.asc -O - | apt-key add -
  rm -rf /etc/apt/sources.list.d/pgdg.list
  sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt/ stretch-pgdg main" >> /etc/apt/sources.list.d/pgdg.list'
  DISTRO=$(lsb_release -i -s  | tr '[:upper:]' '[:lower:]')
  DISTRO_CODENAME=$(lsb_release -c -s  | tr '[:upper:]' '[:lower:]')
  sh -c "wget -qO - https://packages.fluentbit.io/fluentbit.key | sudo apt-key add -"
  rm -rf /etc/apt/sources.list.d/fluentbit-io.list
  sh -c "echo 'deb https://packages.fluentbit.io/$DISTRO/$DISTRO_CODENAME/ $DISTRO_CODENAME main' >> /etc/apt/sources.list.d/fluentbit-io.list"

  apt-get update
  apt-get -y upgrade || exit 3

  # General server install
  apt-get -y install vim iotop htop rsync build-essential rng-tools td-agent-bit acl || exit 4

  # If not test environment, install security packages
  if [ -f /sys/hypervisor/uuid ] && [ $(head -c 3 /sys/hypervisor/uuid) = ec2 ]; then
    apt-get -y install fail2ban shorewall || exit 5
  fi
  apt-get -y install nginx letsencrypt redis-server php7.0-fpm php7.0-xml || exit 6
  apt-get -y install postgresql-10 postgresql-client-10 || exit 6
  apt-get -y install python-pip python-cryptography libssl-dev python-virtualenv || exit 3
  HOME="/root" pip install --upgrade pip | cat || exit 4
  HOME="/root" /usr/local/bin/pip install --upgrade virtualenv | cat
fi

mkdir -p "/home/$API_NAME"

if [ "$RESTART" -eq 1 ]; then
  # Stop all previous installation process
  if pidof systemd > /dev/null; then
    for daemon in $STOPPABLE_SERVICE_LIST; do
      if systemctl is-active --quiet "$daemon" ; then
          echo "Stopping service $daemon"
          systemctl stop "$daemon" 2>/dev/null >/dev/null
      fi
    done
  fi
fi


if [ "$DEPLOY_CONF" -eq 1 ]; then

  # Remove previous virtualenv installation.
  # This will kill all actually running zephycloud services
  #if [ "$(ps -ef | grep "/home/$API_NAME/${API_NAME}_env/bin" | grep -v grep | wc -l)" -ge 1 ]; then
  #    ps -ef | grep "/home/$API_NAME/${API_NAME}_env/bin" | grep -v grep | awk '{print $2}' | xargs kill
  #    sleep 1
  #    if [ "$(ps -ef | grep "/home/$API_NAME/${API_NAME}_env/bin" | grep -v grep | wc -l)" -ge 1 ]; then
  #        ps -ef | grep "/home/$API_NAME/${API_NAME}_env/bin" | grep -v grep | awk '{print $2}' | xargs kill -9
  #    fi
  #fi
  #
  #rm -rf "/home/$API_NAME/${API_NAME}_env"
  #deactivate > /dev/null 2> /dev/null

  if [ ! -e "/home/$API_NAME/${API_NAME}_env/bin/activate" ]; then
      virtualenv "/home/$API_NAME/${API_NAME}_env" || exit 3
  fi
  . "/home/$API_NAME/${API_NAME}_env/bin/activate" || exit 4

  # ------------------------------- API specific requirements -------------------------

  pip install -I alembic | cat
  "$SCRIPT_PATH/install_deps.sh" "$API_NAME" || { echo "specific installation failed with exit code $?" >&2 && exit 10; }

  # ------------------------------- END API specific requirements ---------------------

  deactivate > /dev/null 2> /dev/null
  chown -R "$API_NAME:$API_NAME" "/home/$API_NAME/${API_NAME}_env/"
  echo "done"
  echo ""
fi

if [ "$DEPLOY_DB" -eq 1 ] || [ "$DEPLOY_CONF" -eq 1 ]; then
# ------------------------------- Get local database information -------------------------

  # Get old database password if exists
  if run_pg "SELECT 777 FROM pg_database WHERE datname = '${API_NAME}'" | grep -q 777; then
    DB_EXISTS=1
  else
    DB_EXISTS=0
  fi

  DB_KEEP_PWD=0
  if [ "$DB_EXISTS" -eq 1 ]; then
    if run_pg "SELECT 1 FROM pg_roles WHERE rolname='${API_NAME}'" | grep -q 1; then
      if [ -f "$DEST_PATH/config.conf" ]; then
        DB_PWD="$(get_ini_val "$DEST_PATH/config.conf" "database" "password")"
        if [ -n "$DB_PWD" ]; then
          if PGPASSWORD="$DB_PWD" psql -h 127.0.0.1 -U "$API_NAME" -d "$API_NAME" -tAc 'SELECT 1;' 2>/dev/null | grep -q 1; then
            DB_KEEP_PWD=1
          fi
        fi
      fi
    fi
  fi

  if [ "$DB_KEEP_PWD" -ne 1 ]; then
    DB_PWD="$(date +%s | sha256sum | base64 | head -c 16 ; echo)"
  fi
fi

# ------------------------------- Files installations -------------------------

echo "Installing application files..."

if [ "$DEPLOY_API" -eq 1 ]; then

  # Backup old app if on real server
  rm -rf "$DEST_PATH/app_bkp"
  if [ -e "$DEST_PATH/app" ]; then
      cp -aT "$DEST_PATH/app" "$DEST_PATH/app_bkp"
  fi

  # Copy or mount app
  find "$DEST_PATH/app" -mindepth 1 -delete
  cp -aT "$INSTALL_PATH/src/server" "$DEST_PATH/app"
  chown -R "$API_NAME:$API_NAME" "$DEST_PATH/app"

  # Copy tools
  find "$DEST_PATH/tools" -mindepth 1 -delete
  cp -aT "$INSTALL_PATH/tools/server_tools" "$DEST_PATH/tools"
  chown -R "$API_NAME:$API_NAME" "$DEST_PATH/tools"
  chmod -R g+rX "$DEST_PATH/tools"

  app_tmp_folder="$(get_ini_val "$DEST_PATH/config.conf" "general" "tmp_folder")"
  mkdir -p "$app_tmp_folder"
  chown -R "$API_NAME:$API_NAME" "$DEST_PATH/app"
  chmod u+rx "$DEST_PATH/app/garbage_collector.py"
  chmod u+rx "$DEST_PATH/app/gunicorn_config.py"
  chmod u+rx "$DEST_PATH/app/server.py"
  chmod u+rw "$DEST_PATH/app/web_api.py"
  chmod u+rw "$DEST_PATH/app/websocket_server.py"
fi

if [ "$DEPLOY_DASHBOARD" -eq 1 ]; then
  # Copy dashboard
  if [ "$DEPLOY_CONF" -eq 0 ]; then
    cp "$DEST_PATH/dashboard/app/Config/dashboard.conf" "$INSTALL_PATH/src/dashboard/app/Config/dashboard.conf"
  fi
  find "$DEST_PATH/dashboard" -mindepth 1 -delete
  cp -aT "$INSTALL_PATH/src/dashboard" "$DEST_PATH/dashboard"
  chown -R "$API_NAME:www-data" "$DEST_PATH/dashboard"
  chmod -R g+rX "$DEST_PATH/dashboard"
fi

# copy conf
if [ "$DEPLOY_CONF" -eq 1 ]; then
  cp -f "$CONF_PATH/config.conf" "$DEST_PATH/config.conf"
  sed -i -e 's/%REDIS_HOST%/localhost/g' \
         -e 's/%REDIS_PORT%/6379/g' \
         -e 's/%REDIS_DATA_DB%/3/g' \
         -e 's/%REDIS_PUBSUB_DB%/4/g' \
         -e 's#%SERVER_LOG_OUTPUT%#/var/log/'"$API_NAME"'/'"$API_NAME"'_server.log#g' \
         -e 's#%WEBAPI_LOG_OUTPUT%#/var/log/'"$API_NAME"'/'"$API_NAME"'_webapi.log#g' \
         -e 's#%WEBSOCKET_LOG_OUTPUT%#/var/log/'"$API_NAME"'/'"$API_NAME"'_websocket.log#g' \
         -e 's/%WEBSOCKET_BIND%/localhost/g' \
         -e 's/%WEBSOCKET_PORT%/5000/g' \
         -e 's/%DB_HOST%/localhost/g' \
         -e 's/%DB_PORT%/5432/g' \
         -e 's/%DB_NAME%/'"$API_NAME"'/g' \
         -e 's/%DB_USER%/'"$API_NAME"'/g' \
         -e 's/%DB_PWD%/'"$DB_PWD"'/g' \
         "$DEST_PATH/config.conf"

  cp -f "$CONF_PATH/dashboard.conf" "$DEST_PATH/dashboard/app/Config/dashboard.conf"

  if [ ! -e "$DEST_PATH/cloud_ssh_keys" ]; then
    mkdir -p "$DEST_PATH/cloud_ssh_keys" || exit 12
  fi
  cp -f "$CONF_PATH/cloud_ssh/"* "$DEST_PATH/cloud_ssh_keys/"

  mkdir -p "$DEST_PATH/cloud_ssh_keys/monitoring" || exit 12
  cp -f "$CONF_PATH/id_rsa_monitoring"* "$DEST_PATH/cloud_ssh_keys/monitoring"

  chmod -R 400 "$DEST_PATH/cloud_ssh_keys" || exit 13
  find "$DEST_PATH/cloud_ssh_keys" -name '*.pub' -execdir chmod 600 '{}' \;
  chmod -R u+rX "$DEST_PATH/cloud_ssh_keys" || exit 13
fi

chown -R "$APP_USER:$APP_USER" "$DEST_PATH"
echo "done"
echo ""


# ------------------------------- Database management -------------------------


if [ "$DEPLOY_DB" -eq 1 ]; then

  echo "Initializing database..."

  NEW_MIGRATIONS=0
  if [ ! -d "$MIGRATIONS_PATH" ]; then
    mkdir -p "$MIGRATIONS_PATH"
    chown -R "$API_NAME:$API_NAME" "$MIGRATIONS_PATH"
    chmod 660 "$MIGRATIONS_PATH"
    chmod -R ug+rwX "$MIGRATIONS_PATH"
    NEW_MIGRATIONS=1
  fi

  if [ "$DB_EXISTS" -eq 1 ]; then
    rm -rf "/home/${API_NAME}/database/backup.sql.gz"
    su -l postgres -c "pg_dump '$API_NAME'" | gzip > "/home/${API_NAME}/database/backup.sql.gz"
  fi

  if [ "$DB_KEEP_PWD" -ne 1 ]; then
    if [ "$DB_EXISTS" -eq 1 ]; then
      run_pg "REASSIGN OWNED BY $API_NAME TO postgres" "$API_NAME"
      run_pg "DROP OWNED BY $API_NAME" "$API_NAME"
      run_pg "DROP ROLE IF EXISTS $API_NAME" "$API_NAME"
    fi
    run_pg "DROP ROLE IF EXISTS $API_NAME" || exit 62
    run_pg "CREATE USER $API_NAME WITH ENCRYPTED PASSWORD '$DB_PWD'" || exit 63
    if [ "$DB_EXISTS" -ne 1 ]; then
      run_pg "CREATE DATABASE $API_NAME WITH OWNER $API_NAME ENCODING 'utf8'" || exit 65
    else
      run_pg "ALTER DATABASE $API_NAME OWNER TO $API_NAME" || exit 66
    fi
    run_pg "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ${API_NAME}" "$API_NAME" || exit 67
    run_pg "GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ${API_NAME}" "$API_NAME" || exit 68
    run_pg "GRANT ALL PRIVILEGES ON DATABASE ${API_NAME} TO ${API_NAME}" || exit 69
  else
    if [ "$DB_EXISTS" -ne 1 ]; then
      run_pg "CREATE DATABASE $API_NAME WITH OWNER $API_NAME ENCODING 'utf8'" || exit 65
      run_pg "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ${API_NAME}" "$API_NAME" || exit 67
      run_pg "GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ${API_NAME}" "$API_NAME" || exit 68
      run_pg "GRANT ALL PRIVILEGES ON DATABASE ${API_NAME} TO ${API_NAME}" || exit 69
    fi
  fi

  if grep -qR '^omegaz:' /etc/passwd; then
    run_pg "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO omegaz" "$API_NAME" || exit 67
    run_pg "GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO omegaz" "$API_NAME" || exit 68
    run_pg "GRANT ALL PRIVILEGES ON DATABASE ${API_NAME} TO omegaz" || exit 69
  fi

  ALEMBIC_CONN_STR="postgresql+psycopg2://${API_NAME}:${DB_PWD}@127.0.0.1/${API_NAME}?client_encoding=utf8"
  MIGRATION_PROVIDERS="$(get_ini_val "$DEST_PATH/config.conf" "general" "allowed_providers")"
  mkdir -p "$MIGRATIONS_PATH/db_data"
  mkdir -p "$MIGRATIONS_PATH/versions"
  if grep -F sqlalchemy.url 2>/dev/null "$MIGRATIONS_PATH/alembic.ini" | grep -qF 'sqlite:/'; then
    mv "$MIGRATIONS_PATH" "$DB_PATH/old_sqlite3_migrations"
    if [ -f "$DB_PATH/app.db" ]; then
      mv "$DB_PATH/app.db" "$DB_PATH/old_sqlite3_migrations/app.db"
    fi
    mkdir -p "$MIGRATIONS_PATH/db_data"
    mkdir -p "$MIGRATIONS_PATH/versions"
  fi
  rsync -a -O --no-perms --ignore-existing --exclude='.*' --exclude='*.pyc' "$INSTALL_PATH/db/migrations/versions/" "$MIGRATIONS_PATH/versions/"   || exit 12
  cp "$INSTALL_PATH/db/alembic.production.ini" "$MIGRATIONS_PATH/alembic.ini"
  sed -i -e "s#%CONN_STR%#${ALEMBIC_CONN_STR}#g" -e "s/%API_NAME%/${API_NAME}/g" -e "s#%PROVIDERS%#${MIGRATION_PROVIDERS}#g" -e "s#%DOMAIN%#${SERVER_NAME}#g" "$MIGRATIONS_PATH/alembic.ini"
  cp "$INSTALL_PATH/db/alembic.production_quiet.ini" "$MIGRATIONS_PATH/alembic_quiet.ini"
  sed -i -e "s#%CONN_STR%#${ALEMBIC_CONN_STR}#g" -e "s/%API_NAME%/${API_NAME}/g" -e "s#%PROVIDERS%#${MIGRATION_PROVIDERS}#g" -e "s#%DOMAIN%#${SERVER_NAME}#g" "$MIGRATIONS_PATH/alembic_quiet.ini"
  cp "$INSTALL_PATH/db/migrations/env.py" "$MIGRATIONS_PATH/env.py"
  cp "$INSTALL_PATH/db/migrations/script.py.mako" "$MIGRATIONS_PATH/script.py.mako"
  cp "$INSTALL_PATH/db/current_version.txt" "$MIGRATIONS_PATH/current_version.txt"


  # Run the needed migrations
  TARGET_MIGRATION=$(cat "$MIGRATIONS_PATH/current_version.txt" | head -n1)
  . "/home/$API_NAME/${API_NAME}_env/bin/activate" || exit 12
  if [ "$NEW_MIGRATIONS" -eq 1 ]; then
    (cd "$MIGRATIONS_PATH"; alembic upgrade "$TARGET_MIGRATION") || exit 13
  else
    CURRENT_MIGRATION=$(cd "$MIGRATIONS_PATH"; alembic -c "$MIGRATIONS_PATH/alembic_quiet.ini" current | cut -d' ' -f1) || exit 14
    if  [ -z "$TARGET_MIGRATION" ]; then
      echo "Unable to detect target migration versions" >&2
      exit 15
    fi
    if [ "$CURRENT_MIGRATION" != "$TARGET_MIGRATION" ]; then
      if [ -z "$CURRENT_MIGRATION" ]; then
        CURRENT_MIGRATION_POSITION=2
        TARGET_MIGRATION_POSITION=1
      else
        MIGRATION_HISTORY=$(cd "$MIGRATIONS_PATH"; alembic history | awk '{ print $3; }' | sed 's/,$//') || exit 16
        CURRENT_MIGRATION_POSITION=$(echo "$MIGRATION_HISTORY" | sed -n '/^'"$CURRENT_MIGRATION"'$/=' | xargs) || exit 17
        echo "$CURRENT_MIGRATION_POSITION" | grep -vqE '^[0-9]+$' && { echo "Bad migration position" >&2 ; exit 17; }
        TARGET_MIGRATION_POSITION=$(echo "$MIGRATION_HISTORY" | sed -n '/^'"$TARGET_MIGRATION"'$/=' | xargs ) || exit 18
        echo "$TARGET_MIGRATION_POSITION" | grep -vqE '^[0-9]+$' && { echo "Bad migration position" >&2 ; exit 18; }
      fi
      if [ "$CURRENT_MIGRATION_POSITION" -gt "$TARGET_MIGRATION_POSITION" ]; then
        (cd "$MIGRATIONS_PATH"; alembic upgrade "$TARGET_MIGRATION") || exit 19
      else
        (cd "$MIGRATIONS_PATH"; alembic downgrade "$TARGET_MIGRATION") || exit 20
      fi
    fi
  fi
  deactivate > /dev/null 2> /dev/null
  echo "done"
  echo ""
fi

# ------------------------------- User rights management -------------------------

chown -R "$API_NAME:$API_NAME" "/home/$API_NAME" || exit 21



# ------------------------------- Service management -------------------------

if [ "$DEPLOY_CONF" -eq 1 ]; then
  # install the webserver
  echo "Configuring rng-tools"
  sed -iR "/^HRNGDEVICE/d" /etc/default/rng-tools
  echo "HRNGDEVICE=/dev/urandom" >> /etc/default/rng-tools
  if which systemctl >/dev/null 2>&1; then
    systemctl enable rng-tools.service
    systemctl restart rng-tools.service
  elif which service >/dev/null 2>&1; then
    service rng-tools restart
  fi

  echo "Configuring web server..."
  cp -aT "$INSTALL_FILES/etc/php" "/etc/php"
  rm -f "/etc/php/7.0/fpm/sites-available/${API_NAME}.conf"
  rm -f "/etc/php/7.0/fpm/sites-enabled/${API_NAME}.conf"
  mv "/etc/php/7.0/fpm/sites-available/azg.conf" "/etc/php/7.0/fpm/sites-available/${API_NAME}.conf"
  sed -i 's/%API_NAME%/'"$API_NAME/g" "/etc/php/7.0/fpm/sites-available/${API_NAME}.conf"
  ln -sf "../sites-available/${API_NAME}.conf" "/etc/php/7.0/fpm/sites-enabled/${API_NAME}.conf"
  chmod a+rX /etc/php
  if which systemctl >/dev/null 2>&1; then
    systemctl restart php7.0-fpm.service
  fi

  for file in "$(grep -Rnwl '/etc/nginx/sites-enabled' -e " *${SERVER_NAME} *; *$")"; do
    rm -f "$file"
  done
  for file in "$(grep -Rnwl '/etc/nginx/sites-available' -e " *${SERVER_NAME} *; *$")"; do
    rm -f "$file"
  done

  cp "$INSTALL_FILES/etc/nginx/sites-available/azg_http" "/etc/nginx/sites-available/${API_NAME}_http"
  ln -s "../sites-available/${API_NAME}_http" "/etc/nginx/sites-enabled/${API_NAME}_http"
  sed -i 's/%SERVERNAME%/'"$SERVER_NAME/g" "/etc/nginx/sites-available/${API_NAME}_http"
  nginx -t | exit 40
  systemctl restart nginx
  # Disable letsencrypt for deployement in china until we got the ICP license
  letsencrypt certonly -a webroot --webroot-path=/var/www/html -d "$SERVER_NAME" -m "$ZS_EMAIL" --agree-tos --non-interactive || { echo 'Please check your DNS !!!'; exit 41; }
  rm "/etc/nginx/sites-enabled/${API_NAME}_http"
  cp "$INSTALL_FILES/etc/nginx/sites-available/azg_api" "/etc/nginx/sites-available/${API_NAME}_api"
  sed -i '/letsencrypt/d' /etc/crontab
  echo "57    11  *     *     *     root      letsencrypt renew; service nginx restart" >> /etc/crontab

  ln -sf "../sites-available/${API_NAME}_api" "/etc/nginx/sites-enabled/${API_NAME}_api"
  sed -i 's/%SERVERNAME%/'"$SERVER_NAME/g" "/etc/nginx/sites-available/${API_NAME}_api"
  sed -i 's/%API_NAME%/'"$API_NAME"'/g' "/etc/nginx/sites-available/${API_NAME}_api"
  sed -i 's#%DASHBOARD_PATH%#/home/'"$API_NAME"'/dashboard#' "/etc/nginx/sites-available/${API_NAME}_api"
  sync
  nginx -t 2>&1 | exit 42
  if pidof systemd > /dev/null; then
    systemctl restart nginx
  fi
  echo "done."

  # FIXME: issue with shorewall, had to do hardware restart on server to get ssh access after update
  #echo "Configuring firewall..."
  #if [ -f /sys/hypervisor/uuid ] && [ $(head -c 3 /sys/hypervisor/uuid) = ec2 ]; then
  #    echo "You are on an ec2 instance, no firewall required, however security group should be configured"
  #else
  #    apt-get install -y shorewall
  #    cp -RT "$INSTALL_FILES/etc/shorewall" /etc/shorewall
  #    service shorewall start
  #fi
  #echo "done."



  # Configure rsyslog
  cp -f "$INSTALL_FILES/etc/rsyslog.d/td-agent-bit.conf" "/etc/rsyslog.d/td-agent-bit.conf"
  if which systemctl >/dev/null 2>&1; then
    systemctl restart rsyslog
  fi

  # Configure logrotate
  cp -f "$INSTALL_FILES/etc/logrotate.d/azg" "/etc/logrotate.d/$API_NAME"
  sed -i -r 's/%API_NAME%/'"$API_NAME"'/g' "/etc/logrotate.d/$API_NAME"

  # Configure td-agent-bit
  if which systemctl >/dev/null 2>&1; then
    systemctl stop td-agent-bit
  fi
  mkdir -p /etc/td-agent-bit/services
  mkdir -p /etc/td-agent-bit/parsers
  mkdir -p /etc/td-agent-bit/scripts
  mkdir -p /var/lib/td-agent-bit

  MONITORING_SERVER="$(get_ini_val "$DEST_PATH/config.conf" "log" "log_server")"
  MONITORING_KEY="$(get_ini_val "$DEST_PATH/config.conf" "log" "log_key")"

  rm -rf /etc/td-agent-bit/td-agent-bit.conf.orig
  if [ -e /etc/td-agent-bit/td-agent-bit.conf ]; then
    mv /etc/td-agent-bit/td-agent-bit.conf /etc/td-agent-bit/td-agent-bit.conf.orig
  fi
  HOSTNAME="$(hostname)"
  rm -f "/etc/td-agent-bit/td-agent-bit.conf"
  cp -aT "$INSTALL_FILES/etc/td-agent-bit/td-agent-bit.conf" "/etc/td-agent-bit/td-agent-bit.conf" || exit 30
  sed -i 's/%HOSTNAME%/'"$HOSTNAME/g" "/etc/td-agent-bit/td-agent-bit.conf"
  sed -i 's/%MONITORING_SERVER%/'"$MONITORING_SERVER/g" "/etc/td-agent-bit/td-agent-bit.conf"
  sed -i 's/%MONITORING_KEY%/'"$MONITORING_KEY/g" "/etc/td-agent-bit/td-agent-bit.conf"

  rm -f "/etc/td-agent-bit/scripts/azg_normalize.lua"
  cp -aT "$INSTALL_FILES/etc/td-agent-bit/scripts/azg_normalize.lua" "/etc/td-agent-bit/scripts/azg_normalize.lua" || exit 30

  rm -f "/etc/td-agent-bit/parsers.conf"
  cp -aT "$INSTALL_FILES/etc/td-agent-bit/parsers.conf" "/etc/td-agent-bit/parsers.conf" || exit 30

  for filename in $(ls -1 "$INSTALL_FILES/etc/td-agent-bit/services"); do
    if echo "$filename" | grep -qE "^azg"; then
      dest_filename="$(echo "$filename"  | sed 's/^azg/'"$API_NAME"'/')"
      rm -f "/etc/td-agent-bit/services/$dest_filename"
      cp -aT "$INSTALL_FILES/etc/td-agent-bit/services/$filename" "/etc/td-agent-bit/services/$dest_filename" || exit 30
      sed -i 's/%API_NAME%/'"$API_NAME/g" "/etc/td-agent-bit/services/$dest_filename"
      sed -i 's/%SERVERNAME%/'"$SERVER_NAME/g" "/etc/td-agent-bit/services/$dest_filename"
    else
      rm -rf "/etc/td-agent-bit/services/$filename"
      cp -aT "$INSTALL_FILES/etc/td-agent-bit/services/$filename" "/etc/td-agent-bit/services/$filename" || exit 30
    fi
  done

  if which systemctl >/dev/null 2>&1; then
    systemctl enable td-agent-bit
    systemctl restart td-agent-bit
  fi

  if [ ! -e /usr/local/node_exporter/node_exporter ]; then
    if ! grep -q "^node_exporter:" /etc/passwd ; then
      adduser --system --home /usr/local/node_exporter node_exporter || exit 31
    fi
    wget https://github.com/prometheus/node_exporter/releases/download/v0.18.1/node_exporter-0.18.1.linux-amd64.tar.gz -O /tmp/node_exporter.tgz|| exit 13
    tar xf /tmp/node_exporter.tgz --directory /usr/local/node_exporter --strip-components=1 || exit 14
    chown -R node_exporter:nogroup /usr/local/node_exporter || exit 15
    if which systemctl >/dev/null 2>&1; then
      cp "$INSTALL_FILES/etc/systemd/system/node_exporter.service" "/etc/systemd/system/node_exporter.service"
      chown root:root "/etc/systemd/system/node_exporter.service" || exit 17
      chmod 644 "/etc/systemd/system/node_exporter.service" || exit 18
      systemctl daemon-reload || exit 19
      systemctl enable node_exporter.service || exit 20
    fi
  fi

  # TODO: install and configure postgres_exporter
  # https://github.com/wrouesnel/postgres_exporter/releases/download/v0.8.0/postgres_exporter_v0.8.0_linux-amd64.tar.gz

  # TODO: install and configure named_process_exporter
fi

if [ "$RESTART" -eq 1 ]; then
  if which systemctl >/dev/null 2>&1; then
    echo "Configuring service startup ..."

    if [ "$DEPLOY_CONF" -eq 1 ]; then
      SYSTEMD_FOLDER="$INSTALL_FILES/etc/systemd/system"
      for file in $(ls -1 "$SYSTEMD_FOLDER"); do
        dest_filename="$(echo "$file" | sed 's/apiname/'"$API_NAME"'/')"
        cp "$SYSTEMD_FOLDER/$file" "/etc/systemd/system/$dest_filename"
        sed -i -r 's/%API_NAME%/'"$API_NAME"'/g' "/etc/systemd/system/$dest_filename"
      done
    fi

    systemctl daemon-reload
    systemctl enable postgresql
    systemctl start postgresql

    for daemon in $SERVICE_LIST; do
      systemctl enable "$daemon" 2>&1
    done
    systemctl start "${API_NAME}_files"
    for daemon in $STOPPABLE_SERVICE_LIST; do
        systemctl restart "$daemon"
    done
    if systemctl is-active --quiet "$MAIN_SERVICE" ; then
      echo "Main service already running, reloading main service"
      systemctl reload "$MAIN_SERVICE"
    else
      echo "Start main service"
      systemctl start "$MAIN_SERVICE"
    fi
    systemctl restart nginx
    echo "done"
    echo ""
  elif [ ! -f /.dockerenv ]; then
    echo "You are not running systemd" >&2
    echo "Please check manually how to setup $API_NAME service" >&2
    exit 2
  fi

  # ------------------------------- Checking all service are running -------------------------
  echo ""
  echo "Waiting to services to launch..."
  sleep 3

  echo "Checking services status:"
  for daemon in nginx $SERVICE_LIST; do
    secs=3600                         # Set interval (duration) in seconds.
    endTime=$(( $(date +%s) + 10 )) #  try during 10 sec
    daemon_ok=0
    while [ "$(date +%s)" -lt "$endTime" ] && [ "$daemon_ok" = "0" ]; do
      if systemctl is-active --quiet "$daemon" ; then
        daemon_ok=1
      fi
    done
    if [ "$daemon_ok" = "0" ]; then
      echo "Service $daemon is not running !" >&2
      exit 99
    fi
  done
  systemctl reload sshd
  echo "Ok: $API_NAME services are running"
fi

# ------------------------------- End of the script -------------------------

echo ""
echo "Installation successful"
exit 0
