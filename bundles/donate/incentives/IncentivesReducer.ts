import _ from 'lodash';

import { Bid, Incentive, IncentivesAction } from './IncentiveTypes';
import { ActionFor, ActionTypes } from '../Action';

type IncentivesState = {
  incentives: { [incentiveId: number]: Incentive };
  bids: { [bidId: number]: Bid };
};

const initialState: IncentivesState = {
  incentives: {},
  bids: {},
};

function handleLoadIncentives(state: IncentivesState, action: ActionFor<'LOAD_INCENTIVES'>) {
  const { incentives } = action;
  const incentivesById = _.keyBy(incentives, 'id');

  return {
    ...state,
    incentives: incentivesById,
  };
}

function handleCreateBid(state: IncentivesState, action: ActionFor<'CREATE_BID'>) {
  const { bid } = action;

  return {
    ...state,
    bids: {
      ...state.bids,
      [bid.incentiveId]: bid,
    },
  };
}

function handleDeleteBid(state: IncentivesState, action: ActionFor<'DELETE_BID'>) {
  const { incentiveId } = action;
  const { [incentiveId]: _removedBid, ...filteredBids } = state.bids;

  return {
    ...state,
    bids: filteredBids,
  };
}

export default function reducer(state = initialState, action: IncentivesAction) {
  switch (action.type) {
    case ActionTypes.LOAD_INCENTIVES:
      return handleLoadIncentives(state, action);
    case ActionTypes.CREATE_BID:
      return handleCreateBid(state, action);
    case ActionTypes.DELETE_BID:
      return handleDeleteBid(state, action);
    default:
      return state;
  }
}
