import _ from 'lodash';

export default function dropdowns(state, action) {
  if (action.type === 'DROPDOWN_TOGGLE') {
    return _.assignIn({}, state, { [action.dropdown]: !state[action.dropdown] });
  } else {
    return state || {};
  }
}
