## Ubuntu & Vagrant
    https://app.vagrantup.com/ubuntu/boxes/bionic64


##### Basic
    sudo locale-gen zh_CN.UTF-8
    sudo apt update
    apt list --upgradable
    sudo apt upgrade
    sudo apt install tree
    ssh-keygen -o


##### Python
    sudo apt install python-dev
    sudo apt install python-pip
    mkdir .cache/pip
    sudo pip install --upgrade pip
    sudo pip install ipython


##### NTP
    sudo apt install ntp
    sudo service ntp restart
    timedatectl set-ntp true
    timedatectl status
    timedatectl


##### Zbar 二维码识别
    sudo apt install libzbar0 libzbar-dev
    pip install zbarlight
    
