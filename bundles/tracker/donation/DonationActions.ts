import _ from 'lodash';

import { ActionTypes } from '../Action';
import { Bid, Donation, DonationFormErrors } from './DonationTypes';

export function loadDonation(donation: any, bids: Bid[], formErrors: DonationFormErrors) {
  return {
    type: ActionTypes.LOAD_DONATION,
    donation: {
      name: donation.requestedalias || '',
      email: donation.requestedemail || '',
      wantsEmails: donation.requestedsolicitemail || 'CURR',
      amount: donation.amount || undefined,
      comment: donation.comment || '',
    },
    bids,
    formErrors,
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

export function buildDonationPayload(csrfToken: string, donation: Donation, bids: Bid[]) {
  const bidsformData = bids
    .filter(bid => bid.incentiveId)
    .reduce(
      (acc, bid, index) => ({
        ...acc,
        [`bidsform-${index}-bid`]: bid.incentiveId,
        [`bidsform-${index}-customoptionname`]: bid.customoptionname,
        [`bidsform-${index}-amount`]: bid.amount.toFixed(2),
      }),
      {},
    );

  return {
    csrfmiddlewaretoken: csrfToken,
    requestedvisibility: donation.name === '' ? 'ANON' : 'ALIAS',
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
  };
}

export function submitDonation(donateUrl: string, csrfToken: string, donation: Donation, bids: Bid[]) {
  // Does this seem weird? Yes. So why do this?
  // In short, this lets us abstract "submitting a donation" from the structure
  // of the DOM, easily change the shape of the form data in a single place,
  // and transition to an asynchronous API in the future. We already need to
  // use JavaScript like this anyway to do extra validations across fields and
  // to build the proper form structure, so this is a natural extension.
  const form = document.createElement('form');
  form.action = donateUrl;
  form.method = 'POST';
  form.style.visibility = 'hidden';

  const submissionData = buildDonationPayload(csrfToken, donation, bids);

  _.forEach(submissionData, (value, field) => {
    const input = document.createElement('input');
    input.name = field;
    input.value = value.toString();
    form.appendChild(input);
  });

  document.body.appendChild(form);
  form.submit();
  document.body.removeChild(form);
}
