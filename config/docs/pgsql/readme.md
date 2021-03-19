## PostgreSQL


##### From the command line:
    sudo su - postgres
    psql -f init-dev.sql

##### From the psql prompt:
> \i init-dev.sql

##### Reset database
    \connect kubrickdb;
    DROP SCHEMA public CASCADE;
    CREATE SCHEMA public;


##### 查看使用情况
    select pg_size_pretty(pg_database_size('kubrickdb'));
