## 服务器相关文件目录

### 所有服务相关放在 `/data` 目录下
### 方便非操作系统磁盘挂载扩容


### `/data` 下主要目录 `$ ls /data/`
    logs  main  temp  web-server  workspace


### `/data` 下目录结构 `tree /data/`
    
    /data/
    ├── logs
    │   ├── celery
    │   ├── django
    │   ├── nginx
    │   └── uwsgi
    ├── temp
    ├── redis
    │   ├── dump.rdb
    │   ├── redis.conf -> /data/workspace/kubrick/config/conf/redis/redis.conf
    │   ├── _stderr.log
    │   └── _stdout.log
    └── workspace
    │   ├── kubrick
    │   └── taylor
    ├── supervisor
    │   ├── conf.d
    │   ├── logs
    │   ├── supervisord.conf
    │   ├── supervisord.log
    │   └── supervisord.pid

### 建立软连接

    sudo ln -s /data/workspace/kubrick/config/conf/redis/redis.conf /data/web-server/redis/redis.conf
    sudo ln -s /data/workspace/kubrick/config/conf/supervisor/supervisord.conf /data/web-server/supervisor/supervisord.conf
    sudo ln -s /data/workspace/kubrick/config/conf/supervisor/conf.d/kubrick-dev.conf /data/web-server/supervisor/conf.d/kubrick-dev.conf
    # sudo ln -s /data/workspace/kubrick/config/conf/nginx/nginx.conf /etc/nginx/nginx.conf
    sudo ln -s /data/workspace/kubrick/config/conf/nginx/conf.d/kubrick-dev.conf /etc/nginx/conf.d/kubrick-dev.conf
    
    
    
