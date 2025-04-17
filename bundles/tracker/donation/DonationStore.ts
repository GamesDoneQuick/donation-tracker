import { createSelector } from 'reselect';

import { sum } from '@public/util/reduce';

import * as EventDetailsStore from '@tracker/event_details/EventDetailsStore';
import { StoreState } from '@tracker/Store';

import validateDonationUtil from './validateDonation';

const getDonationState = (state: StoreState) => state.donation.donation;
export const getFormErrors = (state: StoreState) => state.donation.formErrors;

export const getCommentFormErrors = createSelector([getFormErrors], formErrors => formErrors.commentform);

export const getBidsFormErrors = createSelector([getFormErrors], formErrors => formErrors.bidsform);

export const getDonation = getDonationState;

export const getDonationAmount = createSelector([getDonationState], donation => donation.amount);

export const getBids = (state: StoreState) => state.donation.bids;

export const getAllocatedBidTotal = createSelector([getBids], bids => {
  return bids
    .filter(bid => bid.incentiveId)
    .map(b => b.amount)
    .reduce(sum, 0);
});

export const validateDonation = createSelector(
  [getDonationState, getBids, EventDetailsStore.getEventDetails],
  (donation, bids, eventDetails) => validateDonationUtil(eventDetails, donation, bids),
);
