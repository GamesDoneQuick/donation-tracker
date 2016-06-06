import _ from 'underscore';

function modelStatusLoading(state, action) {
    return _.extend({}, state, {[action.model]: 'loading'});
}

function modelStatusSuccess(state, action) {
    return _.extend({}, state, {[action.model]: 'success'});
}

function modelStatusError(state, action) {
    return _.extend({}, state, {[action.model]: 'error'});
}

const modelStatusFuctions = {
    MODEL_STATUS_LOADING: modelStatusLoading,
    MODEL_STATUS_SUCCESS: modelStatusSuccess,
    MODEL_STATUS_ERROR: modelStatusError,
};

export default function status(state, action) {
    if (modelStatusFuctions[action.type]) {
        return modelStatusFuctions[action.type](state, action);
    } else {
        return state || {};
    }
}
