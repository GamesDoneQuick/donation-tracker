import { routerMiddleware } from 'connected-react-router';
import { createBrowserHistory } from 'history';
import { applyMiddleware, createStore } from 'redux';
import thunk from 'redux-thunk';
import { composeWithDevTools } from '@redux-devtools/extension';

import freeze from '@public/util/freeze';

import actions from './actions';
import createRootReducer from './reducers';

const freezeReducer = store => next => action => {
  const result = next(action);
  freeze(store.getState());
  return result;
};

const composeEnhancers = composeWithDevTools({
  // Uncomment to see stacktraces in the devtools for each action fired.
  trace: true,
});

export { actions };

export function createTrackerStore({ history } = {}) {
  history = history || createBrowserHistory();

  const store = createStore(
    createRootReducer(history),
    composeEnhancers(applyMiddleware(freezeReducer, thunk, routerMiddleware(history))),
  );
  store.history = history;
  return store;
}
