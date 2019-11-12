import { ActionTypes } from '../Action';
import * as CurrencyUtils from '../../public/util/currency';

import HTTPUtils from '../../public/util/http';
import { Bid, Donation } from './DonationTypes';

export function loadDonation(donation: any) {
  return {
    type: ActionTypes.LOAD_DONATION,
    donation: {
      name: donation.requestedalias || '',
      nameVisibility: (donation.requestedalias != null ? 'ALIAS' : 'ANON') as 'ALIAS' | 'ANON',
      email: donation.requestedemail || '',
      wantsEmails: donation.requestedsolicitemail || 'CURR',
      amount: donation.amount || undefined,
      comment: donation.comment || '',
    },
  };
}

export function updateDonation(fields: Partial<Donation> = {}) {
  return {
    type: ActionTypes.UPDATE_DONATION,
    fields,
  };
}

export function createBid(bid: Bid) {
  return {
    type: ActionTypes.CREATE_BID,
    bid,
  };
}

export function deleteBid(incentiveId: number) {
  return {
    type: ActionTypes.DELETE_BID,
    incentiveId,
  };
}

// TODO: constantize/store `donateUrl` and `csrftoken` instead of passing them
// manually here.
export function submitDonation(donateUrl: string, csrftoken: string, donation: Donation, bids: Array<Bid>) {
  // NOTE(faulty): this is a stopgap to replicate a standard HTML form
  // submission according to Django's expected form structure.
  const bidsformData = bids.reduce(
    (acc, bid, index) => ({
      ...acc,
      [`bidsform-${index}-bid`]: bid.incentiveId,
      [`bidsform-${index}-customoptionname`]: bid.customoptionname,
      [`bidsform-${index}-amount`]: bid.amount,
    }),
    {},
  );

  console.log(bids, bidsformData);

  console.log({
    csrfmiddlewaretoken: donation,
    requestedvisibility: donation.nameVisibility,
    requestedalias: donation.name,
    requestedemail: donation.email,
    requestedsolicitemail: donation.wantsEmails,
    amount: donation.amount != null ? donation.amount.toFixed(2) : '0.00',
    comment: donation.comment,
    ...bidsformData,
    'bidsform-TOTAL_FORMS': bids.length,
    'bidsform-INITIAL_FORMS': 0,
    'bidsform-MIN_NUM_FORMS': 0,
    'bidsform-MAX_NUM_FORMS': 10,
  });
}
