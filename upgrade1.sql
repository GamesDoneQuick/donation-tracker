ALTER TABLE `BidState` ENGINE=INNODB;
ALTER TABLE `Challenge` ENGINE=INNODB;
ALTER TABLE `ChallengeBid` ENGINE=INNODB;
ALTER TABLE `Choice` ENGINE=INNODB;
ALTER TABLE `ChoiceBid` ENGINE=INNODB;
ALTER TABLE `ChoiceOption` ENGINE=INNODB;
ALTER TABLE `Donation` ENGINE=INNODB;
ALTER TABLE `DonationBidState` ENGINE=INNODB;
ALTER TABLE `DonationDomain` ENGINE=INNODB;
ALTER TABLE `DonationReadState` ENGINE=INNODB;
ALTER TABLE `Donor` ENGINE=INNODB;
ALTER TABLE `Prize` ENGINE=INNODB;
ALTER TABLE `SpeedRun` ENGINE=INNODB;
ALTER TABLE `Donation` ADD COLUMN `commentState` VARCHAR(16) DEFAULT 'PENDING' NOT NULL AFTER `readState` ;
ALTER TABLE `Donation` CHANGE COLUMN `bidState` `bidState` VARCHAR(16) NOT NULL DEFAULT 'PENDING'  , CHANGE COLUMN `readState` `readState` VARCHAR(16) NOT NULL DEFAULT 'PENDING';
CREATE TABLE IF NOT EXISTS `DonationCommentState` (
    `donationCommentStateId` varchar(16) NOT NULL PRIMARY KEY
)
;
ALTER TABLE `DonationCommentState` ENGINE=INNODB;
INSERT INTO DonationCommentState VALUES ('PENDING');
INSERT INTO DonationCommentState VALUES ('ACCEPTED');
INSERT INTO DonationCommentState VALUES ('DENIED');

ALTER TABLE `ChallengeBid` ADD CONSTRAINT `challengeId_refs_challengeId_602ffc05` FOREIGN KEY (`challengeId`) REFERENCES `Challenge` (`challengeId`);
ALTER TABLE `ChoiceOption` ADD CONSTRAINT `choiceId_refs_choiceId_71efa8d4` FOREIGN KEY (`choiceId`) REFERENCES `Choice` (`choiceId`);
ALTER TABLE `ChoiceBid` ADD CONSTRAINT `optionId_refs_optionId_24849baa` FOREIGN KEY (`optionId`) REFERENCES `ChoiceOption` (`optionId`);
ALTER TABLE `ChallengeBid` ADD CONSTRAINT `donationId_refs_donationId_3354ae03` FOREIGN KEY (`donationId`) REFERENCES `Donation` (`donationId`);
ALTER TABLE `ChoiceBid` ADD CONSTRAINT `donationId_refs_donationId_2c936a46` FOREIGN KEY (`donationId`) REFERENCES `Donation` (`donationId`);
ALTER TABLE `Donation` ADD CONSTRAINT `bidState_refs_donationBidStateId_3f1316c5` FOREIGN KEY (`bidState`) REFERENCES `DonationBidState` (`donationBidStateId`);
ALTER TABLE `Donation` ADD CONSTRAINT `commentState_refs_donationCommentStateId_76458b37` FOREIGN KEY (`commentState`) REFERENCES `DonationCommentState` (`donationCommentStateId`);
ALTER TABLE `Donation` ADD CONSTRAINT `domain_refs_donationDomainId_1ffe7019` FOREIGN KEY (`domain`) REFERENCES `DonationDomain` (`donationDomainId`);
ALTER TABLE `Donation` ADD CONSTRAINT `readState_refs_donationReadStateId_65759d57` FOREIGN KEY (`readState`) REFERENCES `DonationReadState` (`donationReadStateId`);
ALTER TABLE `Donation` ADD CONSTRAINT `donorId_refs_donorId_4fba4006` FOREIGN KEY (`donorId`) REFERENCES `Donor` (`donorId`);
ALTER TABLE `Prize` ADD CONSTRAINT `donorId_refs_donorId_7981a8f` FOREIGN KEY (`donorId`) REFERENCES `Donor` (`donorId`);
ALTER TABLE `Challenge` ADD CONSTRAINT `speedRunId_refs_speedRunId_5ab03dfd` FOREIGN KEY (`speedRunId`) REFERENCES `SpeedRun` (`speedRunId`);
ALTER TABLE `Choice` ADD CONSTRAINT `speedRunId_refs_speedRunId_7b163710` FOREIGN KEY (`speedRunId`) REFERENCES `SpeedRun` (`speedRunId`);
