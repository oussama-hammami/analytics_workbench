-- Fix aw_user password (handles already-existing user)
USE `analytics_workbench`;

-- Drop and recreate to guarantee clean credentials
DROP USER IF EXISTS 'aw_user'@'localhost';

CREATE USER 'aw_user'@'localhost'
  IDENTIFIED WITH mysql_native_password BY 'aw_pass_2026';

GRANT ALL PRIVILEGES ON `analytics_workbench`.* TO 'aw_user'@'localhost';
FLUSH PRIVILEGES;

-- Verify
SELECT user, host, plugin FROM mysql.user WHERE user = 'aw_user';
