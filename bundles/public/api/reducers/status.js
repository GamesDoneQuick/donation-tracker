import _ from 'lodash';

function modelStatusLoading(state, action) {
    return _.assignIn({}, state, {[action.model]: 'loading'});
}

function modelStatusSuccess(state, action) {
    return _.assignIn({}, state, {[action.model]: 'success'});
}

function modelStatusError(state, action) {
    return _.assignIn({}, state, {[action.model]: 'error'});
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
