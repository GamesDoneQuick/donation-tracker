import { createSelector } from 'reselect';

const getDonationState = state => state.donation;

export const getDonation = getDonationState;

export const getDonationAmount = createSelector(
  [getDonationState],
  donation => donation.amount,
);
