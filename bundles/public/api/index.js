import { compose, combineReducers, createStore, applyMiddleware } from 'redux';
import thunk from 'redux-thunk';
import { connectRouter, routerMiddleware } from 'connected-react-router';
import { composeWithDevTools } from 'redux-devtools-extension';

import { createBrowserHistory } from 'history';

import freeze from 'ui/public/util/freeze';
import actions from './actions';
import createRootReducer from './reducers';

const history = createBrowserHistory();

const freezeReducer = store => next => action => {
  const result = next(action);
  freeze(store.getState());
  return result;
}

const composeEnhancers = composeWithDevTools({
  // Uncomment to see stacktraces in the devtools for each action fired.
  trace: true,
});

const store = createStore(
    createRootReducer(history),
    composeEnhancers(
        applyMiddleware(
            freezeReducer,
            thunk,
            routerMiddleware(history),
        )
    )
);

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
