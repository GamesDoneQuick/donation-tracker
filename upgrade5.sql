UPDATE Donation WHERE Donation.ReadState = 'AMOUNT_READ' SET Donation.ReadState = 'READ';
UPDATE Donation WHERE Donation.ReadState = 'COMMENT_READ' SET Donation.ReadState = 'READ';