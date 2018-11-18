import _ from 'underscore';

function stateModels(state, type, models) {
    return {
        ...state,
        [type]: models,
    };
}

function modelCollectionReplace(state, action) {
    return stateModels(state, action.model, [...action.models]);
}

function modelCollectionAdd(state, action) {
    return stateModels(
        state,
        action.model,
        _.values(_.extend(_.indexBy((state[action.model] || []).slice(), 'pk'), _.indexBy(action.models, 'pk')))
    );
}

function modelCollectionRemove(state, action) {
    let models = state[action.model] ? state[action.model].models.slice() : [];
    let pks = _.pluck(action.models, 'pk');
    models = _.reject(models, (m) => {
        return _indexOf(pks, m.pk) !== -1;
    });
    return stateModels(state, action.model,  models);
}

function modelSetInternalField(state, action) {
    const models = (state[action.model] || []).slice();
    const model = _.findWhere(models, {pk: action.pk});
    if (!model) {
        return state;
    }
    const _internal = model._internal || {};
    return stateModels(state, action.model, [..._.reject(models, (m) => m.pk === action.pk), {...model, _internal: {..._internal, [action.field]: action.value}}]);
}

let modelCollectionFunctions = {
    MODEL_COLLECTION_REPLACE: modelCollectionReplace,
    MODEL_COLLECTION_ADD: modelCollectionAdd,
    MODEL_COLLECTION_REMOVE: modelCollectionRemove,
    MODEL_SET_INTERNAL_FIELD: modelSetInternalField,
};

export default function models(state, action) {
    if (modelCollectionFunctions[action.type]) {
        return modelCollectionFunctions[action.type](state, action);
    } else {
        return state || {};
    }
}
