import { Donation } from './DonationTypes';
import { ActionTypes } from '../Action';

export function loadDonation(donation: any) {
  return {
    type: ActionTypes.LOAD_DONATION,
    donation: {
      name: donation.requestedalias,
      nameVisibility: donation.requestedalias ? 'ALIAS' : 'ANON',
      email: donation.requestedemail,
      wantsEmails: donation.requestedsolicitemail,
      amount: undefined,
      comment: undefined,
    },
  };
}

export function updateDonation(fields: Partial<Donation> = {}) {
  if (fields.hasOwnProperty('amount')) {
    const parsedAmount = Number(fields.amount);
    fields.amount = parsedAmount === NaN ? undefined : parsedAmount;
  }

  return {
    type: ActionTypes.UPDATE_DONATION,
    fields,
  };
}

export function createBid(bid: { incentiveId: number; customOption: string; amount: number }) {
  return {
    type: ActionTypes.CREATE_BID,
    bid: {
      ...bid,
      customOption: bid.customOption === '' ? undefined : bid.customOption,
    },
  };
}

export function deleteBid(incentiveId: number) {
  return {
    type: ActionTypes.DELETE_BID,
    incentiveId,
  };
}
