import _ from 'underscore';

function modelCollectionReplace(state, action) {
    return _.extend({}, state, {
        [action.model]: action.models.slice()
    });
}

function modelCollectionAdd(state, action) {
    let models = (state[action.model] || []).slice();
    models = _.values(_.extend(_.indexBy(models, 'pk'), _.indexBy(action.models, 'pk')));
    return _.extend({}, state, {[action.model]: models});
}

function modelCollectionRemove(state, action) {
    let models = state[action.model] ? state[action.model].models.slice() : [];
    let pks = _.pluck(action.models, 'pk');
    models = _.reject(models, (m) => {
        return _indexOf(pks, m.pk) !== -1;
    });
    return _.extend({}, state, {[action.model]: models});
}

let modelCollectionFunctions = {
    MODEL_COLLECTION_REPLACE: modelCollectionReplace,
    MODEL_COLLECTION_ADD: modelCollectionAdd,
    MODEL_COLLECTION_REMOVE: modelCollectionRemove,
};

export default function models(state, action) {
    if (modelCollectionFunctions[action.type]) {
        return modelCollectionFunctions[action.type](state, action);
    } else {
        return state || {};
    }
}
