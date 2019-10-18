import _ from 'lodash';

// type EventDetails = {
//   receiverName: string,
//   prizesUrl: string,
//   rulesUrl: string,
//   donateUrl: string,
//   minimumDonation: number,
//   maximumDonation: number,
//   step: number,
// };

const defaultEventDetails = {
  receiverName: "",
  prizesUrl: "",
  rulesUrl: "",
  donateUrl: "",
  minimumDonation: 1,
  maximumDonation: Infinity,
  step: 0.01,
};
const defaultState = {...defaultEventDetails};

const actions = {
  'eventsDetails/LOAD_EVENT_DETAILS': (state, {data}) => {
    return _.merge({...defaultEventDetails}, {
      receiverName: data.receivername,
      prizesUrl: data.prizesUrl,
      rulesUrl: data.rulesUrl,
      donateUrl: data.donateUrl,
      minimumDonation: data.minimumDonation,
      maximumDonation: data.maximumDonation,
      step: data.step,
    });
  },
};



export default function reducer(state = defaultState, action) {
  const func = actions[action.type];
  const newState = func ? func(state, action) : state;
  return newState;
}
