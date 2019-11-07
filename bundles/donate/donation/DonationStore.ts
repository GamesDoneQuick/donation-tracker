import { createSelector } from 'reselect';

import * as CurrencyUtils from '../../public/util/currency';
import * as EventDetailsStore from '../event_details/EventDetailsStore';
import * as IncentiveStore from '../incentives/IncentiveStore';
import { StoreState } from '../Store';

type DonationValidation = {
  valid: boolean;
  errors: Array<{ field: string; message: string }>;
};

const getDonationState = (state: StoreState) => state.donation;

export const getDonation = getDonationState;

export const getDonationAmount = createSelector(
  [getDonationState],
  donation => donation.amount,
);

export const validateDonation = createSelector(
  [getDonationState, IncentiveStore.getBids, EventDetailsStore.getEventDetails],
  (donation, bids, eventDetails): DonationValidation => {
    const validation: DonationValidation = { valid: true, errors: [] };

    if (donation.amount == null || donation.amount < eventDetails.minimumDonation) {
      validation.valid = false;
      validation.errors.push({
        field: 'amount',
        message: `Donation amount must be at least ${CurrencyUtils.asCurrency(eventDetails.minimumDonation)}`,
      });
    }

    return validation;
  },
);
