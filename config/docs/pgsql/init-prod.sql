-- Create kubrickdb
CREATE USER kubrickdb WITH PASSWORD 'kubrickdb';
CREATE DATABASE kubrickdb OWNER kubrickdb;
GRANT ALL PRIVILEGES ON DATABASE kubrickdb TO kubrickdb;
