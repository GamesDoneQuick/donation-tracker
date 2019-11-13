import _ from 'lodash';

import { Bid, Donation, DonationAction } from './DonationTypes';

import { ActionFor, ActionTypes } from '../Action';

type DonationState = {
  donation: Donation;
  bids: { [incentiveId: string]: Bid };
};

const initialState: DonationState = {
  donation: {
    name: '',
    nameVisibility: 'ANON',
    email: '',
    wantsEmails: 'CURR',
    amount: undefined,
    comment: '',
  },
  bids: {},
};

function handleLoadDonation(state: DonationState, action: ActionFor<'LOAD_DONATION'>) {
  return {
    ...state,
    donation: action.donation,
  };
}

function handleUpdateDonation(state: DonationState, action: ActionFor<'UPDATE_DONATION'>) {
  const { fields } = action;
  const donation = _.merge(
    { ...state.donation },
    {
      name: fields.name,
      nameVisibility: fields.name !== '' ? 'ALIAS' : 'ANON',
      email: fields.email,
      wantsEmails: fields.wantsEmails,
      amount: fields.amount,
      comment: fields.comment,
    },
  );

  return {
    ...state,
    donation,
  };
}

function handleCreateBid(state: DonationState, action: ActionFor<'CREATE_BID'>) {
  const { bid } = action;

  return {
    ...state,
    bids: {
      ...state.bids,
      [bid.incentiveId]: bid,
    },
  };
}

function handleDeleteBid(state: DonationState, action: ActionFor<'DELETE_BID'>) {
  const { incentiveId } = action;
  const { [incentiveId]: _removedBid, ...filteredBids } = state.bids;

  return {
    ...state,
    bids: filteredBids,
  };
}

export default function reducer(state = initialState, action: DonationAction) {
  switch (action.type) {
    case ActionTypes.LOAD_DONATION:
      return handleLoadDonation(state, action);
    case ActionTypes.UPDATE_DONATION:
      return handleUpdateDonation(state, action);
    case ActionTypes.CREATE_BID:
      return handleCreateBid(state, action);
    case ActionTypes.DELETE_BID:
      return handleDeleteBid(state, action);
    default:
      return state;
  }
}
