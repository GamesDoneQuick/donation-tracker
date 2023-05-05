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

function modelCollectionReplace(state, action) {
  return stateModels(state, action.model, [...action.models]);
}

function modelCollectionAdd(state, action) {
  return stateModels(
    state,
    action.model,
    _.values(_.assignIn(_.keyBy((state[action.model] || []).slice(), pkOrId), _.keyBy(action.models, pkOrId))),
  );
}

function modelCollectionRemove(state, action) {
  let models = state[action.model] ? state[action.model].models.slice() : [];
  const pks = action.models.map(pkOrId);
  models = _.reject(models, m => {
    return _.indexOf(pks, pkOrId(m)) !== -1;
  });
  return stateModels(state, action.model, models);
}

function modelSetInternalField(state, action) {
  const models = (state[action.model] || []).slice();
  const model = _.find(models, { pk: action.pk });
  if (!model) {
    return state;
  }
  const _internal = model._internal || {};
  return stateModels(state, action.model, [
    ..._.reject(models, m => m.pk === action.pk),
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
