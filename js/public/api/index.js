import _ from 'underscore';
import { compose, combineReducers, createStore, applyMiddleware } from 'redux';
import thunk from 'redux-thunk';
import { routerReducer, routerMiddleware } from 'react-router-redux';
import { devTools, persistState } from 'redux-devtools';

import createHistory from 'history/createBrowserHistory';

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

const history = createHistory();
const middleware = routerMiddleware(history);

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
    history,
};

export default {
    actions,
    store,
    history,
};
