import _ from 'lodash';

import { Donation, DonationAction } from './DonationTypes';

import { ActionFor, ActionTypes } from '../Action';

type DonationState = Donation;

const initialState: DonationState = {
  name: '',
  nameVisibility: 'ANON',
  email: '',
  wantsEmails: 'CURR',
  amount: undefined,
  comment: '',
};

function handleLoadDonation(state: DonationState, action: ActionFor<'LOAD_DONATION'>) {
  return {
    ...state,
    ...action.donation,
  };
}

function handleUpdateDonation(state: DonationState, action: ActionFor<'UPDATE_DONATION'>) {
  const { fields } = action;
  return _.merge(
    { ...state },
    {
      name: fields.name,
      nameVisibility: !!fields.name ? 'ALIAS' : 'ANON',
      email: fields.email,
      wantsEmails: fields.wantsEmails,
      amount: fields.amount,
      comment: fields.comment,
    },
  );
}

export default function reducer(state = initialState, action: DonationAction) {
  switch (action.type) {
    case ActionTypes.LOAD_DONATION:
      return handleLoadDonation(state, action);
    case ActionTypes.UPDATE_DONATION:
      return handleUpdateDonation(state, action);
    default:
      return state;
  }
}
