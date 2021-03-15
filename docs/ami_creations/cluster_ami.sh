# ----------------- Common part, AMI generation -----------------------------------------
MAIN_LOCALE="fr_FR.UTF-8"

export LANGUAGE="$MAIN_LOCALE"
export LANG="$MAIN_LOCALE"
export LC_ALL="$MAIN_LOCALE"
sudo locale-gen "$MAIN_LOCALE"
sudo DEBIAN_FRONTEND=noninteractive dpkg-reconfigure locales

sudo sh -c "wget -O - http://dl.openfoam.org/gpg.key | sudo apt-key add -"
sudo add-apt-repository http://dl.openfoam.org/ubuntu

sudo DEBIAN_FRONTEND=noninteractive apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get upgrade -y

sudo DEBIAN_FRONTEND=noninteractive apt-get install -y openfoam4 nfs-common

sudo sed -i '/openfoam4\/etc\/bashrc/d' /root/.bashrc
sudo sh -c "echo '. /opt/openfoam4/etc/bashrc' >> /root/.bashrc"
sed -i '/openfoam4\/etc\/bashrc/d' /home/ubuntu/.bashrc
echo '. /opt/openfoam4/etc/bashrc' >> /home/ubuntu/.bashrc

source /opt/openfoam4/etc/bashrc
mkdir -p $(echo $FOAM_RUN)


# ------------------------ Master specific, run by python cluster -------------------------

sudo DEBIAN_FRONTEND=noninteractive apt-get install -y nfs-kernel-server

ssh-keygen -t rsa -b 4096 -C "openfoam_master" -f "/home/ubuntu/.ssh/id_rsa" -q -N ""

sudo sed -i '/OpenFOAM/d' /etc/exports
sudo sh -c "echo '/home/ubuntu/OpenFOAM  *(rw,sync,no_subtree_check)' >> /etc/exports"
sudo exportfs -ra
sudo service nfs-kernel-server start
# - se connecter en ssh à toutes les instances pour zapper le probleme de la première connection
# - mettre les ips privées dans un fichier "machines"

# ------------------------ Slave specific, run by python cluster -------------------------
# on slaves
mkdir -p /home/ubuntu/OpenFOAM
find /home/ubuntu/OpenFOAM -mindepth 1 -delete
# - copie de la clef du master vers  /home/ubuntu/.ssh/authorized_keys
sudo mount IP_PRIV_DU_MASTER:/home/ubuntu/OpenFOAM /home/ubuntu/OpenFOAM
