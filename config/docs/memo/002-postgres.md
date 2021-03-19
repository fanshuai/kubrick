## Postgres


##### Postgis
    # Auto install postgres 10
    sudo apt update
    sudo apt install postgis


##### Psycopg2
    sudo apt-get build-dep python-psycopg2
    # E: You must put some 'source' URIs in your sources.list
    sudo vi /etc/apt/sources.list
    deb http://archive.ubuntu.com/ubuntu bionic main restricted
    deb-src http://archive.ubuntu.com/ubuntu bionic main restricted
    sudo apt update


##### Remote access
    sudo vi /etc/postgresql/10/main/postgresql.conf
    listen_addresses = '*'
    sudo vi /etc/postgresql/10/main/pg_hba.conf
    # IPv4 local connections:
    host    all             all             127.0.0.1/32            md5
    host    all             all             0.0.0.0/0               md5
    sudo service postgresql restart


##### 阿里云 ECS
    只安装客户端
    sudo apt-get install postgresql-client


##### Learn
1. [PostgreSQL新手入门](http://www.ruanyifeng.com/blog/2013/12/getting_started_with_postgresql.html)
2. [使用PostgreSQL进行中文全文检索](https://cloud.tencent.com/developer/article/1012830)
