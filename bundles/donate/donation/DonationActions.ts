import { ActionTypes } from '../Action';
import * as CurrencyUtils from '../../public/util/currency';

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
