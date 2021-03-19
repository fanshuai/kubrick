### Ubuntu Xenial 16.04 (xenialbox)


### 本地开发环境配置
    vagrant vm box: ubuntu/xenial64


#### Vagrant 密码初始化重置, PyCharm Vagrant 远程解释器需要
    sudo passwd ubuntu
    # vi Vagrantfile
    # config.ssh.username = "ubuntu"
    # config.ssh.password = "ubuntu"


#### Vagrant 相关配置参考 `./Vagrantfile`


#### 本机 HOST 相关设置 `sudo vi /etc/hosts`

    192.168.33.10   vagrant
