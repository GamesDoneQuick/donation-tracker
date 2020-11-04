import _ from 'lodash';

import HTTPUtil from '../../util/http';
import Endpoints from '../../../tracker/Endpoints';

function onModelStatusLoad(model) {
  return {
    type: 'MODEL_STATUS_LOADING',
    model,
  };
}

function onModelStatusSuccess(model) {
  return {
    type: 'MODEL_STATUS_SUCCESS',
    model,
  };
}

function onModelStatusError(model) {
  return {
    type: 'MODEL_STATUS_ERROR',
    model,
  };
}

function onModelCollectionReplace(model, models) {
  return {
    type: 'MODEL_COLLECTION_REPLACE',
    model,
    models,
  };
}

function onModelCollectionAdd(model, models) {
  return {
    type: 'MODEL_COLLECTION_ADD',
    model,
    models,
  };
}

// eslint-disable-next-line no-unused-vars
function onModelCollectionRemove(model, models) {
  return {
    type: 'MODEL_COLLECTION_REMOVE',
    model,
    models,
  };
}

// TODO: Better solution than this
const fetchMap = {
  speedrun: 'run',
};

// TODO: I hate this
const reverseMap = {
  allbids: 'bid',
  bidtarget: 'bid',
};

function loadModels(model, params, additive) {
  const fetchModel = fetchMap[model] || model;
  const realModel = reverseMap[model] || model;
  return dispatch => {
    dispatch(onModelStatusLoad(model));
    return HTTPUtil.get(Endpoints.SEARCH, {
      ...params,
      type: fetchModel,
    })
      .then(models => {
        dispatch(onModelStatusSuccess(model));
        const action = additive ? onModelCollectionAdd : onModelCollectionReplace;
        dispatch(
          action(
            realModel,
            models.reduce((acc, v) => {
              if (v.model.toLowerCase() === `tracker.${realModel}`.toLowerCase()) {
                v.fields.pk = v.pk;
                acc.push(v.fields);
              }
              return acc;
            }, []),
          ),
        );
      })
      .catch(error => {
        dispatch(onModelStatusError(model));
        if (!additive) {
          dispatch(onModelCollectionReplace(realModel, []));
        }
      });
  };
}

function onNewDraftModel(model) {
  return {
    type: 'MODEL_NEW_DRAFT',
    model,
  };
}

function newDraftModel(model) {
  return dispatch => {
    dispatch(onNewDraftModel(model));
  };
}

function onDeleteDraftModel(model) {
  return {
    type: 'MODEL_DELETE_DRAFT',
    model,
  };
}

function deleteDraftModel(model) {
  return dispatch => {
    dispatch(onDeleteDraftModel(model));
  };
}

function onDraftModelUpdateField(model, pk, field, value) {
  return {
    type: 'MODEL_DRAFT_UPDATE_FIELD',
    model,
    pk,
    field,
    value,
  };
}

function updateDraftModelField(model, pk, field, value) {
  return dispatch => {
    dispatch(onDraftModelUpdateField(model, pk, field, value));
  };
}

function onSetInternalModelField(model, pk, field, value) {
  return {
    type: 'MODEL_SET_INTERNAL_FIELD',
    model,
    pk,
    field,
    value,
  };
}

function setInternalModelField(model, pk, field, value) {
  return dispatch => {
    dispatch(onSetInternalModelField(model, pk, field, value));
  };
}

function onSaveDraftModelError(model, error, fields) {
  return {
    type: 'MODEL_SAVE_DRAFT_ERROR',
    model,
    error,
    fields,
  };
}

function saveDraftModels(models) {
  return dispatch => {
    models.forEach(model => {
      dispatch(setInternalModelField(model.type, model.pk, 'saving', true));
      const url = model.pk < 0 ? Endpoints.ADD : Endpoints.EDIT;

      HTTPUtil.post(
        url,
        {
          type: fetchMap[model.type] || model.type,
          id: model.pk,
          ..._.omit(model.fields, (v, k) => k.startsWith('_')),
        },
        {
          encoder: HTTPUtil.Encoders.QUERY,
        },
      )
        .then(savedModels => {
          const models = savedModels.reduce((acc, v) => {
            if (v.model.toLowerCase() === `tracker.${model.type}`.toLowerCase()) {
              v.fields.pk = v.pk;
              acc.push(v.fields);
            } else {
              console.warn('unexpected model', v);
            }
            return acc;
          }, []);
          dispatch(onModelCollectionAdd(model.type, models));
          dispatch(onDeleteDraftModel(model));
        })
        .catch(response => {
          const json = response.json();
          dispatch(onSaveDraftModelError(model, json ? json.error : response.body(), json ? json.fields : {}));
        })
        .finally(() => {
          dispatch(setInternalModelField(model.type, model.pk, 'saving', false));
        });
    });
  };
}

function saveField(model, field, value) {
  return dispatch => {
    if (model.pk) {
      dispatch(setInternalModelField(model.type, model.pk, 'saving', true));
      if (value === undefined || value === null) {
        value = 'None';
      }
      HTTPUtil.post(
        Endpoints.EDIT,
        {
          type: fetchMap[model.type] || model.type,
          id: model.pk,
          [field]: value,
        },
        {
          encoder: HTTPUtil.Encoders.QUERY,
        },
      )
        .then(savedModels => {
          dispatch(
            onModelCollectionAdd(
              model.type,
              savedModels.reduce((o, v) => {
                if (v.model.toLowerCase() === `tracker.${model.type}`.toLowerCase()) {
                  v.fields.pk = v.pk;
                  o.push(v.fields);
                } else {
                  console.warn('unexpected model', v);
                }
                return o;
              }, []),
            ),
          );
        })
        .catch(response => {
          const json = response.json();
          dispatch(onSaveDraftModelError(model, json ? json.error : response.body(), json ? json.fields : {}));
        })
        .finally(() => {
          dispatch(setInternalModelField(model.type, model.pk, 'saving', false));
        });
    }
  };
}

function command(command) {
  return dispatch => {
    return HTTPUtil.post(
      Endpoints.COMMAND,
      {
        data: JSON.stringify({
          command: command.type,
          ...command.params,
        }),
      },
      {
        encoder: HTTPUtil.Encoders.QUERY,
      },
    )
      .then(models => {
        const m = models[0];
        if (!m) return;

        const type = m.model.split('.')[1];
        dispatch(
          onModelCollectionAdd(
            type,
            models.reduce((acc, v) => {
              if (v.model.toLowerCase() === `tracker.${type}`.toLowerCase()) {
                v.fields.pk = v.pk;
                acc.push(v.fields);
              } else {
                console.warn('unexpected model', v);
              }
              return acc;
            }, []),
          ),
        );
        if (typeof command.done === 'function') {
          command.done();
        }
      })
      .catch(() => {
        if (typeof command.fail === 'function') {
          command.fail();
        }
      })
      .finally(() => {
        if (typeof command.always === 'function') {
          command.always();
        }
      });
  };
}

export default {
  loadModels,
  newDraftModel,
  deleteDraftModel,
  updateDraftModelField,
  setInternalModelField,
  saveDraftModels,
  saveField,
  command,
};
