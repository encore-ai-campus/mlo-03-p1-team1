-- Run as a DBA after replacing ALL placeholders. Do not commit filled credentials.
-- Database/table identifiers below are examples to align with docs/setup.md.
CREATE DATABASE IF NOT EXISTS culturepick CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- Replace <backend-ip> with the backend server's source address (never '%' in production).
CREATE USER 'culturepick_app'@'<backend-ip>' IDENTIFIED BY '<app-password>';
GRANT SELECT, INSERT, UPDATE, DELETE ON culturepick.* TO 'culturepick_app'@'<backend-ip>';
-- Migrations and collectors should use separate accounts.
CREATE USER 'culturepick_migrator'@'<migration-host-ip>' IDENTIFIED BY '<migration-password>';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, DROP, INDEX, REFERENCES ON culturepick.* TO 'culturepick_migrator'@'<migration-host-ip>';
-- A dedicated collector needs SELECT/INSERT/UPDATE on contents only.
CREATE USER 'culturepick_collector'@'<collector-ip>' IDENTIFIED BY '<collector-password>';
GRANT SELECT, INSERT, UPDATE ON culturepick.contents TO 'culturepick_collector'@'<collector-ip>';
