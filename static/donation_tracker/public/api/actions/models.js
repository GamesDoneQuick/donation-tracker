import _ from 'underscore';

function onModelStatusLoad(model) {
    return {
        type: 'MODEL_STATUS_LOADING', model
    };
}

function onModelStatusSuccess(model) {
    return {
        type: 'MODEL_STATUS_SUCCESS', model
    };
}

function onModelStatusError(model) {
    return {
        type: 'MODEL_STATUS_ERROR', model
    };
}

function onModelCollectionReplace(model, models, compare) {
    return {
        type: 'MODEL_COLLECTION_REPLACE', model, models, compare
    };
}

function onModelCollectionAdd(model, models, compare) {
    return {
        type: 'MODEL_COLLECTION_ADD', model, models, compare
    };
}

function onModelCollectionRemove(model, models, compare) {
    return {
        type: 'MODEL_COLLECTION_REMOVE', model, models, compare
    };
}

function loadModels(model, params, compare, additive) {
    return (dispatch) => {
        dispatch(onModelStatusLoad(model));
        $.get(`${API_ROOT}search`, _.extend({type: model}, params || {})).
            done((models) => {
                dispatch(onModelStatusSuccess(model));
                const func = additive ? onModelCollectionAdd : onModelCollectionReplace;
                dispatch(func(`${model}s`,
                    models.reduce((o, v) => {
                        if (v.model === `tracker.${model}`) {
                            v.fields.pk = v.pk;
                            o.push(v.fields);
                        }
                        return o;
                    }, []),
                    compare
                ));
            }).
            fail((data) => {
                dispatch(onModelStatusError(model));
                if (!additive) {
                    dispatch(onModelCollectionReplace(`${model}s`, []));
                }
            });
    }
}

function onNewDraftModel(model) {
    return {
        type: 'MODEL_NEW_DRAFT', model
    };
}

function newDraftModel(model) {
    return (dispatch) => {
        dispatch(onNewDraftModel(model));
    };
}

function onDeleteDraftModel(model) {
    return {
        type: 'MODEL_DELETE_DRAFT', model
    }
}

function deleteDraftModel(model) {
    return (dispatch) => {
        dispatch(onDeleteDraftModel(model));
    };
}

function onDraftModelUpdateField(model, pk, field, value) {
    return {
        type: 'MODEL_DRAFT_UPDATE_FIELD', model, pk, field, value
    };
}

function updateDraftModelField(model, pk, field, value) {
    return (dispatch) => {
        dispatch(onDraftModelUpdateField(model, pk, field, value));
    };
}

function onSaveDraftModelStart(model) {
    return {
        type: 'MODEL_SAVE_DRAFT_START', model
    };
}

function onSaveDraftModelError(model, error, fields) {
    return {
        type: 'MODEL_SAVE_DRAFT_ERROR', model, error, fields
    };
}

function saveDraftModels(models, compare) {
    return (dispatch) => {
        _.each(models, (m) => {
            dispatch(onSaveDraftModelStart(m));
            const url = m.pk < 0 ? `${API_ROOT}add/` : `${API_ROOT}edit/`;
            $.post(url, _.extend({type: m.type, id: m.pk}, m.fields)).
                done((savedModels) => {
                    dispatch(onModelCollectionAdd(`${m.type}s`,
                        savedModels.reduce((o, v) => {
                            if (v.model === `tracker.${m.type}`) {
                                v.fields.pk = v.pk;
                                o.push(v.fields);
                            } else {
                                console.warn('unexpected model', v);
                            }
                            return o;
                        }, []),
                        compare
                    ));
                    dispatch(onDeleteDraftModel(m));
                }).
                fail((data) => {
                    const json = data.responseJSON;
                    dispatch(onSaveDraftModelError(m, json ? json.error : data, json ? json.fields : {}));
                });
        });
    }
}

function command(params, compare) {
    return (dispatch) => {
        $.post(`${API_ROOT}command/`, {
            data: JSON.stringify(params)
        }).done((models) => {
            const m = models[0];
            if (!m) { return; }
            const type = m.model.split('.')[1];
            dispatch(onModelCollectionAdd(`${type}s`,
                models.reduce((o, v) => {
                    if (v.model === `tracker.${type}`) {
                        v.fields.pk = v.pk;
                        o.push(v.fields);
                    } else {
                        console.warn('unexpected model', v);
                    }
                    return o;
                }, []),
                compare
            ));
        });
    }
}

module.exports = {
    loadModels,
    newDraftModel,
    deleteDraftModel,
    updateDraftModelField,
    saveDraftModels,
    command,
};
