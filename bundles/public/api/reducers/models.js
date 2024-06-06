import _ from 'lodash';

function pkOrId(model) {
  return model.pk || model.id;
}

function stateModels(state, type, models) {
  return {
    ...state,
    [type]: models,
  };
}

function normalizeToId(model) {
  const { pk, ...rest } = model;
  return {
    ...rest,
    id: pkOrId(model),
  };
}

function excludeModels(models, idsToExclude) {
  return models.filter(m => !idsToExclude.includes(m.id));
}

function modelCollectionReplace(state, action) {
  return stateModels(state, action.model, Array.prototype.map.call(action.models, normalizeToId));
}

function modelCollectionAdd(state, action) {
  const normalized = Array.prototype.map.call(action.models, normalizeToId);
  return stateModels(state, action.model, [
    ...excludeModels(state[action.model] || [], normalized.map(pkOrId)),
    ...normalized,
  ]);
}

function modelCollectionRemove(state, action) {
  return stateModels(
    state,
    action.model,
    (state[action.model] || []).filter(m => !action.ids.includes(m.id)),
  );
}

function modelSetInternalField(state, action) {
  const models = state[action.model] || [];
  const model = models.find(m => m.id === pkOrId(action));
  if (!model) {
    return state;
  }
  const _internal = model._internal || {};
  return stateModels(state, action.model, [
    ...excludeModels(models, [pkOrId(action)]),
    { ...model, _internal: { ..._internal, [action.field]: action.value } },
  ]);
}

const modelCollectionFunctions = {
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
