import actions from './actions';
import { status, drafts, models, dropdowns } from './reducers';
import { compose, combineReducers, createStore, applyMiddleware } from 'redux';
import { devTools, persistState } from 'redux-devtools';
import thunk from 'redux-thunk';
import _ from 'underscore';

const reducers = combineReducers({
    status,
    drafts,
    models,
    dropdowns,
});

const store = (__DEVTOOLS__ ?
    compose(
        applyMiddleware(thunk),
        devTools(),
        persistState(window.location.href.match(/[?&]debug_session=([^&]+)\b/))
    )
    :
    applyMiddleware(thunk)
)(createStore)(reducers);

module.exports = {
    actions,
    store,
};
