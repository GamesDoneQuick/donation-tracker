import _ from 'underscore';
import { compose, combineReducers, createStore, applyMiddleware } from 'redux';
import thunk from 'redux-thunk';
import { routerReducer } from 'react-router-redux';
import { devTools, persistState } from 'redux-devtools';

import DevTools from 'ui/devtools';
import actions from './actions';
import reducers from './reducers';
import freeze from 'ui/public/util/freeze';

const combined = combineReducers({...reducers, routing: routerReducer});

function freezeReducer(state = {}, action) {
    const newState = combined(state, action);
    if (newState !== state) {
        return freeze(newState);
    } else {
        return state;
    }
}

function getDebugSessionKey() {
    const matches = window.location.href.match(/[?&]debug_session=([^&#]+)\b/);
    return (matches && matches.length > 0)? matches[1] : null;
}

const store = (__DEVTOOLS__ ?
    compose(
        applyMiddleware(thunk),
        DevTools.instrument(),
        persistState(getDebugSessionKey())
    )
    :
    applyMiddleware(thunk)
)(createStore)(freezeReducer);

export {
    actions,
    store,
};

export default {
    actions,
    store,
};
