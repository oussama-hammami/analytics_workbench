-- =============================================================================
--  Analytics Workbench — Bootstrap SQL
--  Run with:  sudo mysql < add_admin.sql
--
--  This script:
--    1. Creates the database
--    2. Creates a dedicated MySQL app-user (aw_user) with password auth
--    3. Creates the required tables
--    4. Inserts the superadmin  (email: admin  /  password: admin)
-- =============================================================================

-- 1. Database
CREATE DATABASE IF NOT EXISTS `analytics_workbench`
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE `analytics_workbench`;

-- 2. App MySQL user (password auth — works from Python without sudo)
CREATE USER IF NOT EXISTS 'aw_user'@'localhost'
  IDENTIFIED WITH mysql_native_password BY 'aw_pass_2026';

GRANT ALL PRIVILEGES ON `analytics_workbench`.* TO 'aw_user'@'localhost';
FLUSH PRIVILEGES;

-- 3. Tables
CREATE TABLE IF NOT EXISTS `aw_users` (
  `id`         INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `name`       VARCHAR(100) NOT NULL,
  `email`      VARCHAR(150) NOT NULL,
  `password`   VARCHAR(255) NOT NULL,
  `role`       ENUM('superadmin','admin','viewer') NOT NULL DEFAULT 'viewer',
  `is_active`  TINYINT(1)   NOT NULL DEFAULT 1,
  `last_login` TIMESTAMP    NULL,
  `created_at` TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `aw_settings` (
  `id`            INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `setting_key`   VARCHAR(100) NOT NULL,
  `setting_value` LONGTEXT,
  `autoload`      TINYINT(1)   NOT NULL DEFAULT 1,
  `created_at`    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_key` (`setting_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `aw_api_keys` (
  `id`            INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `key_name`      VARCHAR(100) NOT NULL,
  `service`       VARCHAR(100) NOT NULL DEFAULT '',
  `key_encrypted` TEXT         NOT NULL,
  `key_preview`   VARCHAR(24)  NOT NULL,
  `created_by`    INT UNSIGNED NOT NULL DEFAULT 0,
  `created_at`    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_key_name` (`key_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT IGNORE INTO `aw_settings` (`setting_key`, `setting_value`) VALUES
  ('app_version',       '1.0.0'),
  ('install_date',       NOW()),
  ('max_upload_mb',      '50'),
  ('maintenance_mode',   '0');

-- 4. Superadmin  (email: admin / password: admin)
INSERT INTO `aw_users` (name, email, password, role, is_active)
VALUES (
  'Admin',
  'admin',
  '$2b$12$7J1D0Zbm4JbN7KbWcAifUuXEsJgbVb3usC8eeDFPXATqbyVgjK02O',
  'superadmin',
  1
)
ON DUPLICATE KEY UPDATE
  password  = VALUES(password),
  role      = 'superadmin',
  is_active = 1;

SELECT '========================================='   AS '';
SELECT 'Bootstrap complete!'                         AS '';
SELECT 'Login  →  email: admin  /  pw: admin'        AS '';
SELECT 'DB user: aw_user  /  pw: aw_pass_2026'       AS '';
SELECT '========================================='   AS '';
