import { combineReducers } from 'redux';

import drafts from './drafts';
import dropdowns from './dropdowns';
import models from './models';
import singletons from './singletons';
import status from './status';

const createRootReducer = () =>
  combineReducers({
    drafts,
    models,
    status,
    dropdowns,
    singletons,
  });

export default createRootReducer;
