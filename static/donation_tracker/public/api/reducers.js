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

function status(state, action) {
    if (modelStatusFuctions[action.type]) {
        console.log('status', state, action);
        return modelStatusFuctions[action.type](state, action);
    } else {
        return state || {};
    }
}

function modelNewDraft(state, action) {
    const m = action.model;
    const type = `${m.type}s`;
    let newState = {};
    let models = newState[type] = _.extend({}, state[type] || {});
    let keys = [0, ..._.map(Object.keys(models), pk => parseInt(pk))]; // are you kidding me with this
    let pk = m.pk ? m.pk : (_.min(keys) - 1);
    models[pk] = _.extend({ pk: pk }, models[pk] || {}, _.omit(action.model, ['type']));
    return _.extend({}, state, newState);
}

function modelDeleteDraft(state, action) {
    const m = action.model;
    const type = `${m.type}s`;
    let newState = {...state};
    let models = newState[type] = _.extend({}, state[type] || {});
    delete models[m.pk];
    return newState;
}

function modelDraftUpdateField(state, action) {
    let newState = {};
    const type = `${action.model}s`;
    let models = newState[type] = _.extend({}, state[type]);
    let model = _.extend({}, models[action.pk]);
    model[action.field] = action.value;
    newState[type][action.pk] = model;
    return _.extend({}, state, newState);
}

function modelDraftSaveStart(state, action) {
    const m = action.model;
    const type = `${m.type}s`;
    let newState = {};
    let models = newState[type] = _.extend({}, state[type] || {});
    models[m.pk] = _.extend({}, models[m.pk] || {}, { _saving: true });
    return _.extend({}, state, newState);
}

function modelSaveError(state, action) {
    const m = action.model;
    const type = `${m.type}s`;
    let newState = {};
    let models = newState[type] = _.extend({}, state[type] || {});
    models[m.pk] = _.extend({}, models[m.pk] || {}, { _saving: false, _error: action.error, _fields: action.fields });
    return _.extend({}, state, newState);
}

const modelDraftFunctions = {
    MODEL_NEW_DRAFT: modelNewDraft,
    MODEL_DELETE_DRAFT: modelDeleteDraft,
    MODEL_DRAFT_UPDATE_FIELD: modelDraftUpdateField,
    MODEL_SAVE_DRAFT_START: modelDraftSaveStart,
    MODEL_SAVE_DRAFT_ERROR: modelSaveError,
};

function drafts(state, action) {
    if (modelDraftFunctions[action.type]) {
        console.log('drafts', state, action);
        return modelDraftFunctions[action.type](state, action);
    } else {
        return state || {};
    }
}

function modelCollectionReplace(state, action) {
    return _.extend({}, state, {
        [action.model]: action.compare ? action.models.slice().sort(action.compare) : action.models.slice()
    });
}

function modelCollectionAdd(state, action) {
    let models = (state[action.model] || []).slice();
    models = _.values(_.extend(_.indexBy(models, 'pk'), _.indexBy(action.models, 'pk')));
    if (action.compare) {
        models.sort(action.compare);
    }
    return _.extend({}, state, {[action.model]: models});
}

function modelCollectionRemove(state, action) {
    let models = state[action.model] ? state[action.model].models.slice() : [];
    let pks = _.pluck(action.models, 'pk');
    models = _.reject(models, (m) => {
        return _indexOf(pks, m.pk) !== -1;
    });
    if (action.compare) {
        models.sort(action.compare);
    }
    return _.extend({}, state, {[action.model]: models});
}

let modelCollectionFunctions = {
    MODEL_COLLECTION_REPLACE: modelCollectionReplace,
    MODEL_COLLECTION_ADD: modelCollectionAdd,
    MODEL_COLLECTION_REMOVE: modelCollectionRemove,
};

function models(state, action) {
    if (modelCollectionFunctions[action.type]) {
        console.log('models', state, action);
        return modelCollectionFunctions[action.type](state, action);
    } else {
        return state || {};
    }
}

function dropdowns(state, action) {
    if (action.type === 'DROPDOWN_TOGGLE') {
        console.log('dropdowns', state, action);
        return _.extend({}, state, {[action.dropdown]: !state[action.dropdown]});
    } else {
        return state || {};
    }
}

module.exports = {
    status,
    drafts,
    models,
    dropdowns,
};
