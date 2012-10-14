ALTER TABLE `SpeedRun` CHANGE COLUMN `sortKey` `sortKey` INT(11) NULL, DROP INDEX `order`;
CREATE INDEX `SpeedRun_7926d0c3` ON `SpeedRun` (`sortKey`);