-- Reference only: run as a local DBA ON THE REPLICA after replacing passwords.
-- Do not run the master provisioning permissions.sql here.
-- Current schema: culture. Credentials belong in each backend's ignored .env.
CREATE USER 'culturepick_reader'@'192.168.0.156' IDENTIFIED BY '<reader-password>';
CREATE USER 'culturepick_reader'@'192.168.0.157' IDENTIFIED BY '<reader-password>';
GRANT SELECT ON culture.* TO 'culturepick_reader'@'192.168.0.156';
GRANT SELECT ON culture.* TO 'culturepick_reader'@'192.168.0.157';
-- Do not grant DML/DDL, ALL PRIVILEGES, SUPER or READ ONLY ADMIN to readers.
SET GLOBAL read_only=ON;
-- Also persist read_only=ON in the replica's MariaDB configuration.
-- Replication threads remain able to apply master transactions.
