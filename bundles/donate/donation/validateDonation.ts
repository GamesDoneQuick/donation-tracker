import _ from 'lodash';

import { EventDetails } from '../event_details/EventDetailsTypes';
import { Bid, Donation, DonationValidation } from './DonationTypes';

export default function validateDonation(
  eventDetails: EventDetails,
  donation: Donation,
  bids: Array<Bid>,
): DonationValidation {
  const sumOfBids = _.sumBy(bids, 'amount');

  if (donation.amount == null) {
    return { valid: false, errors: [{ field: 'amount', message: 'Donation amount is not set' }] };
  }

  if (donation.amount < eventDetails.minimumDonation) {
    return {
      valid: false,
      errors: [
        { field: 'amount', message: `Donation amount is below the allowed minimum (${eventDetails.minimumDonation})` },
      ],
    };
  }

  if (donation.amount > eventDetails.maximumDonation) {
    return {
      valid: false,
      errors: [
        { field: 'amount', message: `Donation amount is above the allowed maximum (${eventDetails.maximumDonation})` },
      ],
    };
  }

  if (bids.length > 10) {
    return { valid: false, errors: [{ field: 'bids', message: 'Only 10 bids can be set per donation.' }] };
  }

  if (bids.length > 0) {
    if (sumOfBids > donation.amount) {
      return {
        valid: false,
        errors: [{ field: 'bid amounts', message: 'Sum of bid amounts exceeds donation total.' }],
      };
    }

    if (sumOfBids > donation.amount) {
      return {
        valid: false,
        errors: [{ field: 'bid amounts', message: 'Sum of bid amounts is lower than donation total.' }],
      };
    }
  }

  bids.forEach(bid => {
    const incentive = eventDetails.availableIncentives[bid.incentiveId];
    if (
      incentive != null &&
      incentive.maxlength != null &&
      bid.customoptionname &&
      bid.customoptionname.length > incentive.maxlength
    ) {
      return {
        valid: false,
        errors: [
          {
            field: 'bid',
            message: `New option name for ${incentive.name} is too long (max ${incentive.maxlength})`,
          },
        ],
      };
    }
  });

  return { valid: true, errors: [] };
}
