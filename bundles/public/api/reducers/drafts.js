import _ from 'lodash';

function modelNewDraft(state, action) {
  const m = action.model;
  const type = m.type;
  const newState = {};
  const models = (newState[type] = _.assignIn({}, state[type] || {}));
  const keys = [0, ..._.map(Object.keys(models), pk => parseInt(pk))]; // are you kidding me with this
  const pk = m.pk ? m.pk : _.min(keys) - 1;
  models[pk] = _.assignIn(
    { pk: pk },
    models[pk] || {},
    _.omit(action.model, (v, k) => k === 'type' || k.startsWith('_')),
  );
  return _.assignIn({}, state, newState);
}

function modelDeleteDraft(state, action) {
  const m = action.model;
  const type = m.type;
  const newState = { ...state };
  const models = (newState[type] = _.assignIn({}, state[type] || {}));
  delete models[m.pk];
  return newState;
}

function modelDraftUpdateField(state, action) {
  const newState = {};
  const type = action.model;
  const models = (newState[type] = _.assignIn({}, state[type]));
  const model = _.assignIn({}, models[action.pk]);
  model[action.field] = action.value;
  newState[type][action.pk] = model;
  return _.assignIn({}, state, newState);
}

function modelSaveError(state, action) {
  const m = action.model;
  const type = m.type;
  const newState = {};
  const models = (newState[m.type] = _.assignIn({}, state[type] || {}));
  models[m.pk] = _.assignIn(
    {},
    models[m.pk] || {},
    { _error: action.error, _fields: action.fields },
    _.omit(action.model, ['type']),
  );
  return _.assignIn({}, state, newState);
}

const modelDraftFunctions = {
  MODEL_NEW_DRAFT: modelNewDraft,
  MODEL_DELETE_DRAFT: modelDeleteDraft,
  MODEL_DRAFT_UPDATE_FIELD: modelDraftUpdateField,
  MODEL_SAVE_DRAFT_ERROR: modelSaveError,
};

export default function drafts(state, action) {
  if (modelDraftFunctions[action.type]) {
    return modelDraftFunctions[action.type](state, action);
  } else {
    return state || {};
  }
}
