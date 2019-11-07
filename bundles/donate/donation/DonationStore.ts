import { createSelector } from 'reselect';

import { StoreState } from '../Store';

const getDonationState = (state: StoreState) => state.donation;

export const getDonation = getDonationState;

export const getDonationAmount = createSelector(
  [getDonationState],
  donation => donation.amount,
);
