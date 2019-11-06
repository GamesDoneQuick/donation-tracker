import _ from 'lodash';

// type Incentive = {
//   id: number,
//   amount: number,
//   name: string,
//   customOption: string,
//   parent?: {
//     id: number,
//     name: string,
//     custom: boolean,
//     maxlength: number,
//     description: string,
//   }),
//   runname: string,
//   count: number,
//   goal: number,
//   description: string,
// };
//
//
// // Okay so this gets funky. `id` is _either_:
// //  - the id of the incentive being bid on directly, in the case of simple goal
// //    incentives, or
// //  - the id of the bid option selected for an incentive with choices to select
// //    from, _or_
// //  - the id of the _incentive_ being bid on, with `customOption` being set as
// //    the name to use for a new choice being nominated.
// type Bid = {
//   incentiveId: number,
//   amount: number,
//   customOption: ?string
// };

const defaultState = {
  incentives: {},
  bids: {},
};

const actions = {
  'incentives/LOAD_INCENTIVES': (state, { data }) => {
    const { incentives } = data;
    const incentivesById = _.keyBy(incentives, 'id');

    return {
      ...state,
      incentives: incentivesById,
    };
  },

  'incentives/CREATE_BID': (state, { data }) => {
    const { bid } = data;

    return {
      ...state,
      bids: {
        ...state.bids,
        [bid.incentiveId]: bid,
      },
    };
  },

  'incentives/DELETE_BID': (state, { data }) => {
    const { incentiveId } = data;
    const { [incentiveId]: _removedBid, ...filteredBids } = state.bids;

    console.log(incentiveId, state.bids, filteredBids);

    return {
      ...state,
      bids: filteredBids,
    };
  },
};

export default function reducer(state = defaultState, action) {
  const func = actions[action.type];
  const newState = func ? func(state, action) : state;
  return newState;
}
