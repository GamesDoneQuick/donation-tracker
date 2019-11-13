import _ from 'lodash';
import validator from 'validator';

import { EventDetails } from '../event_details/EventDetailsTypes';
import { MAX_BIDS_PER_DONATION } from './DonationConstants';
import { Bid, Donation, Validation } from './DonationTypes';

export default function validateDonation(eventDetails: EventDetails, donation: Donation, bids: Array<Bid>): Validation {
  const sumOfBids = _.sumBy(bids, 'amount');

  const errors = [];

  if (donation.amount == null) {
    errors.push({ field: 'amount', message: 'Donation amount is not set' });
  } else {
    if (donation.amount < eventDetails.minimumDonation) {
      errors.push({
        field: 'amount',
        message: `Donation amount is below the allowed minimum (${eventDetails.minimumDonation})`,
      });
    }

    if (donation.amount > eventDetails.maximumDonation) {
      errors.push({
        field: 'amount',
        message: `Donation amount is above the allowed maximum (${eventDetails.maximumDonation})`,
      });
    }

    if (bids.length > MAX_BIDS_PER_DONATION) {
      errors.push({ field: 'bids', message: `Only ${MAX_BIDS_PER_DONATION} bids can be set per donation.` });
    }

    if (bids.length > 0) {
      if (sumOfBids > donation.amount) {
        errors.push({ field: 'bid amounts', message: 'Sum of bid amounts exceeds donation total.' });
      }

      if (sumOfBids < donation.amount) {
        errors.push({ field: 'bid amounts', message: 'Sum of bid amounts is lower than donation total.' });
      }
    }
  }

  if (donation.email !== '' && !validator.isEmail(donation.email)) {
    errors.push({ field: 'email', message: 'Email is not a valid email address' });
  }

  bids.forEach(bid => {
    const incentive = eventDetails.availableIncentives[bid.incentiveId];
    if (
      incentive != null &&
      incentive.maxlength != null &&
      bid.customoptionname &&
      bid.customoptionname.length > incentive.maxlength
    ) {
      errors.push({
        field: 'bid',
        message: `New option name for ${incentive.name} is too long (max ${incentive.maxlength})`,
      });
    }
  });

  return {
    valid: errors.length === 0,
    errors,
  };
}
