import _ from 'underscore';

export default function dropdowns(state, action) {
    if (action.type === 'DROPDOWN_TOGGLE') {
        return _.extend({}, state, {[action.dropdown]: !state[action.dropdown]});
    } else {
        return state || {};
    }
}
