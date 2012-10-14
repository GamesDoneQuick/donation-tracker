ALTER TABLE `Prize` ADD COLUMN `minimumBid` DECIMAL(20,2) NOT NULL DEFAULT 5.00  AFTER `description` , ADD COLUMN `startGame` INT(11) AFTER `minimumBid`, ADD COLUMN `endGame` INT(11)  AFTER `startGame`;
ALTER TABLE `Prize` ADD CONSTRAINT `startGame_refs_id_507a23c6` FOREIGN KEY (`startGame`) REFERENCES `SpeedRun` (`id`);
ALTER TABLE `Prize` ADD CONSTRAINT `endGame_refs_id_507a23c6` FOREIGN KEY (`endGame`) REFERENCES `SpeedRun` (`id`);
CREATE INDEX `Prize_23fe92dc` ON `Prize` (`startGame`);
CREATE INDEX `Prize_3202557f` ON `Prize` (`endGame`);