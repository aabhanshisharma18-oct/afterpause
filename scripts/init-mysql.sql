-- Run as a database administrator after creating the afterpause user.
CREATE DATABASE IF NOT EXISTS afterpause_dev CHARACTER SET utf8mb4;
CREATE DATABASE IF NOT EXISTS afterpause_demo CHARACTER SET utf8mb4;
CREATE DATABASE IF NOT EXISTS afterpause_test CHARACTER SET utf8mb4;
GRANT ALL ON afterpause_dev.* TO 'afterpause'@'%';
GRANT ALL ON afterpause_demo.* TO 'afterpause'@'%';
GRANT ALL ON afterpause_test.* TO 'afterpause'@'%';
