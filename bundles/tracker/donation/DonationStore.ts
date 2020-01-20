import _ from 'lodash';
import { createSelector } from 'reselect';

import * as EventDetailsStore from '../event_details/EventDetailsStore';
import { StoreState } from '../Store';
import validateDonationUtil from './validateDonation';

const getDonationState = (state: StoreState) => state.donation.donation;
export const getFormErrors = (state: StoreState) => state.donation.formErrors;

export const getCommentFormErrors = createSelector(
  [getFormErrors],
  formErrors => formErrors.commentform,
);

export const getBidsFormErrors = createSelector(
  [getFormErrors],
  formErrors => formErrors.bidsform,
);

export const getDonation = getDonationState;

export const getDonationAmount = createSelector(
  [getDonationState],
  donation => donation.amount,
);

export const getBids = (state: StoreState) => state.donation.bids;

export const getAllocatedBidTotal = createSelector(
  [getBids],
  bids => {
    if (bids.length === 0) return 0;
    return _.sumBy(bids.filter(bid => bid.incentiveId), 'amount');
  },
);

export const validateDonation = createSelector(
  [getDonationState, getBids, EventDetailsStore.getEventDetails],
  (donation, bids, eventDetails) => validateDonationUtil(eventDetails, donation, bids),
);
