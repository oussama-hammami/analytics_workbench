-- ─────────────────────────────────────────────────────────────────────────────
-- Analytics Workbench — Database Schema
-- Version  : 1.0.0
-- Charset  : utf8mb4 / utf8mb4_unicode_ci
--
-- This file is a reference copy. The installer applies the schema
-- automatically via PDO. You can also import this file manually via
-- phpMyAdmin or the CLI: mysql -u USER -p DB_NAME < install.sql
--
-- Table prefix default: aw_  (configurable during installation)
-- ─────────────────────────────────────────────────────────────────────────────

SET NAMES utf8mb4;
SET time_zone = '+00:00';

-- ── Users ─────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS `aw_users` (
  `id`         INT UNSIGNED    NOT NULL AUTO_INCREMENT,
  `name`       VARCHAR(100)    NOT NULL,
  `email`      VARCHAR(150)    NOT NULL,
  `password`   VARCHAR(255)    NOT NULL                        COMMENT 'bcrypt hash',
  `role`       ENUM('superadmin','admin','viewer')
               NOT NULL DEFAULT 'viewer',
  `is_active`  TINYINT(1)      NOT NULL DEFAULT 1,
  `last_login` TIMESTAMP       NULL,
  `created_at` TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP
                                        ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ── Settings ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS `aw_settings` (
  `id`            INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `setting_key`   VARCHAR(100) NOT NULL,
  `setting_value` LONGTEXT,
  `autoload`      TINYINT(1)   NOT NULL DEFAULT 1              COMMENT '1 = load on boot',
  `created_at`    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
                                        ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_key` (`setting_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ── Default settings seed ────────────────────────────────────────────────────
INSERT IGNORE INTO `aw_settings` (`setting_key`, `setting_value`, `autoload`) VALUES
  ('app_version',        '1.0.0', 1),
  ('install_date',        NOW(),  1),
  ('max_upload_mb',       '50',   1),
  ('allow_registration',  '0',    1);
