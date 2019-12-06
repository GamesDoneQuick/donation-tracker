import _ from 'lodash';

import { ActionFor, ActionTypes } from '../Action';
import { Prize, PrizeAction } from './PrizeTypes';

type PrizesState = {
  prizes: { [id: string]: Prize };
  loading: boolean;
};

const initialState: PrizesState = {
  prizes: {},
  loading: false,
};

function handleFetchPrizesStarted(state: PrizesState, action: ActionFor<'FETCH_PRIZES_STARTED'>) {
  return {
    ...state,
    loading: true,
  };
}

function handleFetchPrizesSuccess(state: PrizesState, action: ActionFor<'FETCH_PRIZES_SUCCESS'>) {
  const { prizes } = action;

  return {
    ...state,
    prizes: {
      ...state.prizes,
      ..._.keyBy(prizes, 'id'),
    },
    loading: false,
  };
}

function handleFetchPrizesFailed(state: PrizesState, action: ActionFor<'FETCH_PRIZES_FAILED'>) {
  return {
    ...state,
    loading: false,
  };
}

export default function reducer(state = initialState, action: PrizeAction) {
  switch (action.type) {
    case ActionTypes.FETCH_PRIZES_STARTED:
      return handleFetchPrizesStarted(state, action);
    case ActionTypes.FETCH_PRIZES_SUCCESS:
      return handleFetchPrizesSuccess(state, action);
    case ActionTypes.FETCH_PRIZES_FAILED:
      return handleFetchPrizesFailed(state, action);
    default:
      return state;
  }
}
