import _ from 'lodash';

import { ActionFor, ActionTypes } from '@tracker/Action';

import { Bid, Donation, DonationAction, DonationFormErrors } from './DonationTypes';

type DonationState = {
  donation: Donation;
  bids: Bid[];
  formErrors: DonationFormErrors;
};

const initialState: DonationState = {
  donation: {
    name: '',
    email: '',
    wantsEmails: 'CURR',
    amount: undefined,
    comment: '',
  },
  // TODO: sum bid amount?
  bids: [],
  formErrors: { bidsform: [], commentform: {} },
};

function handleLoadDonation(state: DonationState, action: ActionFor<'LOAD_DONATION'>) {
  return {
    ...state,
    donation: action.donation,
    bids: action.bids,
    formErrors: action.formErrors,
  };
}

function handleUpdateDonation(state: DonationState, action: ActionFor<'UPDATE_DONATION'>) {
  const { fields } = action;
  const donation = _.merge(
    { ...state.donation },
    {
      name: fields.name,
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
  let { bid } = action;

  const existingBid = state.bids.find(old => old.incentiveId === bid.incentiveId);

  if (existingBid) {
    bid = { ...bid, amount: bid.amount + existingBid.amount };
  }

  return {
    ...state,
    bids: [...state.bids.filter(old => old.incentiveId && old.incentiveId !== bid.incentiveId), bid],
    formErrors: {
      ...state.formErrors,
      bidsform: [],
    },
  };
}

function handleDeleteBid(state: DonationState, action: ActionFor<'DELETE_BID'>) {
  const { incentiveId } = action;

  return {
    ...state,
    bids: state.bids.filter(bid => bid.incentiveId && bid.incentiveId !== incentiveId),
    formErrors: {
      ...state.formErrors,
      bidsform: [],
    },
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
