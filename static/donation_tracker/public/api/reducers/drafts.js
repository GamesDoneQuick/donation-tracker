import _ from 'underscore';

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
    models[m.pk] = _.extend({}, models[m.pk] || {}, { _saving: false, _error: action.error, _fields: action.fields}, _.omit(action.model, ['type']));
    return _.extend({}, state, newState);
}

const modelDraftFunctions = {
    MODEL_NEW_DRAFT: modelNewDraft,
    MODEL_DELETE_DRAFT: modelDeleteDraft,
    MODEL_DRAFT_UPDATE_FIELD: modelDraftUpdateField,
    MODEL_SAVE_DRAFT_START: modelDraftSaveStart,
    MODEL_SAVE_DRAFT_ERROR: modelSaveError,
};

export default function drafts(state, action) {
    if (modelDraftFunctions[action.type]) {
        return modelDraftFunctions[action.type](state, action);
    } else {
        return state || {};
    }
}
