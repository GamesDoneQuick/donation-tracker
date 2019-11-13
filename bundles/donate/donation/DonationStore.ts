import _ from 'lodash';
import { createSelector } from 'reselect';

import * as CurrencyUtils from '../../public/util/currency';
import * as EventDetailsStore from '../event_details/EventDetailsStore';
import { StoreState } from '../Store';
import validateDonationUtil from './validateDonation';

const getDonationState = (state: StoreState) => state.donation.donation;
const getBidsById = (state: StoreState) => state.donation.bids;

export const getDonation = getDonationState;

export const getDonationAmount = createSelector(
  [getDonationState],
  donation => donation.amount,
);

export const getBids = createSelector(
  [getBidsById],
  bidsById => Object.values(bidsById),
);

export const getAllocatedBidTotal = createSelector(
  [getBids],
  bids => {
    if (bids.length == 0) return 0;
    return _.sumBy(bids, 'amount');
  },
);

export const validateDonation = createSelector(
  [getDonationState, getBids, EventDetailsStore.getEventDetails],
  (donation, bids, eventDetails) => validateDonationUtil(eventDetails, donation, bids),
);
