import _ from 'lodash';

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

// Is this weird? Yes.
// Why is this happening? It lets the DOM (and the rest of the app in
// general) be abstracted from the implied structure of Django's formsets and . It
// also makes it easier to transition to an asynchronous API in the future,
// since only this function has to change.
export function submitDonation(donateUrl: string, csrfToken: string, donation: Donation, bids: Array<Bid>) {
  const bidsformData = bids.reduce(
    (acc, bid, index) => ({
      ...acc,
      [`bidsform-${index}-bid`]: bid.incentiveId,
      [`bidsform-${index}-customoptionname`]: bid.customoptionname,
      [`bidsform-${index}-amount`]: bid.amount,
    }),
    {},
  );

  const submissionData = {
    csrfmiddlewaretoken: csrfToken,
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
    'prizeForm-TOTAL_FORMS': 0,
    'prizeForm-INITIAL_FORMS': 0,
    'prizeForm-MIN_NUM_FORMS': 0,
    'prizeForm-MAX_NUM_FORMS': 10,
  };

  const form = document.createElement('form');
  form.method = 'POST';
  form.action = donateUrl;

  _.forEach(submissionData, (value, field) => {
    const input = document.createElement('input');
    input.name = field;
    input.value = value;
    form.appendChild(input);
  });

  document.body.appendChild(form);

  form.submit();
}
