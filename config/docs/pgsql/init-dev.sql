-- Create kubrickdb
DROP DATABASE IF EXISTS kubrickdb;
DROP USER IF EXISTS kubrickdb;

CREATE USER kubrickdb WITH PASSWORD 'kubrickdb';
ALTER ROLE kubrickdb SUPERUSER;
CREATE DATABASE kubrickdb OWNER kubrickdb;
GRANT ALL PRIVILEGES ON DATABASE kubrickdb TO kubrickdb;
\CONNECT kubrickdb;
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;