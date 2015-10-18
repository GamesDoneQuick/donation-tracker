import React from 'react';
import { connect } from 'react-redux';
import _ from 'underscore';
import dateFormat from 'dateformat';

import { actions } from '../../public/api';
import Spinner from '../../public/spinner';
import SpeedRunTable from './speedrun_table'

const { PropTypes } = React;

class ScheduleEditor extends React.Component {
    constructor(props) {
        super(props);

        this.saveModel_ = this.saveModel_.bind(this);
        this.editModel_ = this.editModel_.bind(this);
        this.cancelEdit_ = this.cancelEdit_.bind(this);
        this.newSpeedRun_ = this.newSpeedRun_.bind(this);
        this.updateField_ = this.updateField_.bind(this);
    }

    render() {
        const { speedRuns, events, drafts, status, moveSpeedRun, saveField } = this.props;
        const { event } = this.props.params;
        const { saveModel_, editModel_, cancelEdit_, newSpeedRun_, updateField_, } = this;
        const loading = status.speedRun === 'loading' || status.event === 'loading';
        return (
            <Spinner spinning={loading}>
                {(status.speedRun === 'success' ?
                    <SpeedRunTable
                        event={event ? _.findWhere(events, {pk: parseInt(event)}) : null}
                        drafts={drafts}
                        speedRuns={speedRuns}
                        saveModel={saveModel_}
                        editModel={editModel_}
                        cancelEdit={cancelEdit_}
                        newSpeedRun={newSpeedRun_}
                        moveSpeedRun={moveSpeedRun}
                        saveField={(model, field, value) => saveField({type: 'speedRun', ...model}, field, value)}
                        updateField={updateField_} />
                    : null)}
            </Spinner>
        );
    }

    componentWillReceiveProps(newProps) {
        if (this.props.params.event !== newProps.params.event) {
            this.refreshSpeedRuns_(newProps.params.event);
        }
    }

    componentWillMount() {
        this.refreshSpeedRuns_(this.props.params.event);
    }

    refreshSpeedRuns_(event) {
        const { status } = this.props;
        if (status.event !== 'loading' && status.event !== 'success') {
            this.props.loadModels('event');
        }
        if ((status.speedRun !== 'loading' && status.speedRun !== 'success') || event !== this.props.event) {
            this.props.loadModels(
                'speedRun',
                {event: event, all: 1}
            );
        }
    }

    saveModel_(pk, fields) {
        this.props.saveDraftModels([{type: 'speedRun', pk, fields}]);
    }

    editModel_(model) {
        this.props.newDraftModel({type: 'speedRun', ...model});
    }

    cancelEdit_(model) {
        this.props.deleteDraftModel({type: 'speedRun', ...model});
    }

    newSpeedRun_() {
        this.props.newDraftModel({type: 'speedRun'});
    }

    updateField_(pk, field, value) {
        this.props.updateDraftModelField('speedRun', pk, field, value);
    }
}

function select(state) {
    const { models, drafts, status } = state;
    const { events, speedRuns } = models;
    return {
        events,
        speedRuns,
        status,
        drafts: drafts.speedRuns || {},
    };
}

function dispatch(dispatch) {
    return {
        loadModels: (model, params, additive) => {
            dispatch(actions.models.loadModels(model, params, additive));
        },
        moveSpeedRun: (source, destination, before) => {
            dispatch(actions.models.command({
                    command: 'MoveSpeedRun',
                    moving: source,
                    other: destination,
                    before: before ? 1 : 0,
                }))
        },
        saveField: (model, field, value) => {
            dispatch(actions.models.saveField(model, field, value));
        },
        newDraftModel: (model) => {
            dispatch(actions.models.newDraftModel(model));
        },
        deleteDraftModel: (model) => {
            dispatch(actions.models.deleteDraftModel(model));
        },
        updateDraftModelField: (type, pk, field, value) => {
            dispatch(actions.models.updateDraftModelField(type, pk, field, value));
        },
        saveDraftModels: (models) => {
            dispatch(actions.models.saveDraftModels(models));
        },
    };
}

ScheduleEditor = connect(select, dispatch)(ScheduleEditor);

export default ScheduleEditor;
