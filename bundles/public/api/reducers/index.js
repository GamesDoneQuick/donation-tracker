import { combineReducers } from 'redux';
import { connectRouter } from 'connected-react-router';

import drafts from './drafts';
import models from './models';
import status from './status';
import dropdowns from './dropdowns';
import singletons from './singletons';

const createRootReducer = (history) => combineReducers({
  router: connectRouter(history),
  drafts,
  models,
  status,
  dropdowns,
  singletons,
});

export default createRootReducer;
