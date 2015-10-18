import React from 'react';
import { DropTarget, DragSource } from 'react-dnd';
import { connect } from 'react-redux';
import ErrorList from '../public/error_list';
import Spinner from '../public/spinner';
import FormField from '../public/form_field';
import _ from 'underscore';
import dateFormat from 'dateformat';
import { actions } from '../public/api';

let { PropTypes } = React;

function orderSort(a, b) {
    if (a.order === null && b.order === null) {
        return 0;
    } else if (a.order !== null && b.order === null) {
        return -1;
    } else if (a.order === null && b.order !== null) {
        return 1;
    } else if (a.order < b.order) {
        return -1;
    } else {
        return 1;
    }
}

class OrderTarget extends React.Component {
    render() {
        const {
            target,
            targetType,
            targetProps,
            connectDragSource,
            nullOrder,
            spinning,
        } = this.props;
        const TargetType = targetType; // needs to be uppercase or the compiler will think it's an html tag
        return (
            <Spinner spinning={spinning}>
                {connectDragSource(
                    <span style={{cursor: 'move'}}>
                    { target ?
                        [
                        <TargetType
                            key='before'
                            before={true}
                            {...targetProps}/>,
                        <TargetType
                            key='after'
                            before={false}
                            {...targetProps}/>,
                        nullOrder ?
                            <img
                                key='null'
                                src={STATIC_URL + 'admin/img/icon_deletelink.gif'}
                                onClick={nullOrder} />
                            :
                            null
                        ]
                        :
                        <img src={STATIC_URL + 'asc.png'} />
                    }
                    </span>
                )}
            </Spinner>
        );
    }
}

OrderTarget.propTypes = {
    target: PropTypes.bool.isRequired,
    targetType: PropTypes.func.isRequired,
    connectDragSource: PropTypes.func.isRequired,
    spinning: PropTypes.bool.isRequired,
};

class SpeedRunDropTarget extends React.Component {
    render() {
        const { before, isOver, canDrop, connectDropTarget } = this.props;
        return connectDropTarget(
            <span
                style={{
                    width: '50%',
                    backgroundColor: isOver && canDrop ? 'green' : 'inherit',
                    float: before ? 'left' : 'right'
                }}>
                <img src={STATIC_URL + (before ? 'prev.png' : 'next.png')} />
            </span>
        );
    }
}

const speedRunTarget = {
    drop: function(props, monitor) {
        return {
            action: function(source_pk) {
                props.moveSpeedRun(source_pk, props.pk, props.before);
            }
        };
    },

    canDrop: function(props, monitor) {
        return props.legalMove(monitor.getItem() ? monitor.getItem().source_pk : null);
    },
};

SpeedRunDropTarget = DropTarget('SpeedRun', speedRunTarget, function collect(connect, monitor) {
    return {
        connectDropTarget: connect.dropTarget(),
        isOver: monitor.isOver(),
        canDrop: monitor.canDrop(),
    };
})(SpeedRunDropTarget);

const speedRunSource = {
    beginDrag: function(props) {
        return {source_pk: props.speedRun.pk};
    },

    endDrag: function(props, monitor) {
        const result = monitor.getDropResult();
        if (result && result.action) {
            result.action(props.speedRun.pk);
        }
    },
};

class SpeedRun extends React.Component {
    constructor(props) {
        super(props);
        this.legalMove_ = this.legalMove_.bind(this);
        this.cancel_ = this.cancel_.bind(this);
        this.save_ = this.save_.bind(this);
        this.edit_ = this.edit_.bind(this);
        this.modify_ = this.modify_.bind(this);
    }

    render() {
        const { speedRun, moveSpeedRun, draft, isDragging, connectDragSource, connectDragPreview, saveField } = this.props;
        const fieldErrors = draft ? (draft._fields || {}) : {};
        const { legalMove_, cancel_, save_, edit_, modify_ } = this;
        return (
            <tr style={{opacity: isDragging ? 0.5 : 1}}>
                <td className='small'>
                    {(speedRun && speedRun.order !== null && speedRun.starttime !== null) ? dateFormat(Date.parse(speedRun.starttime)) : 'Unscheduled' }
                </td>
                <td style={{textAlign: 'center'}}>
                    <OrderTarget
                        spinning={(draft && draft._saving) || false}
                        connectDragSource={connectDragSource}
                        nullOrder={saveField.bind(null, 'order', null)}
                        target={!!speedRun.order}
                        targetType={SpeedRunDropTarget}
                        targetProps={{
                            pk: speedRun.pk,
                            legalMove: legalMove_,
                            moveSpeedRun: moveSpeedRun,
                        }}
                        />
                </td>
                {draft ?
                    [
                    <td key='name'>
                        {connectDragPreview(<FormField name='name' value={draft.name} modify={modify_} />)}
                        <ErrorList errors={fieldErrors.name} />
                    </td>,
                    <td key='deprecated_runners'>
                        <FormField name='deprecated_runners' value={draft.deprecated_runners} modify={modify_} />
                        <ErrorList errors={fieldErrors.deprecated_runners} />
                    </td>,
                    <td key='console'>
                        <FormField name='console' value={draft.console} modify={modify_} />
                        <ErrorList errors={fieldErrors.console} />
                    </td>,
                    <td key='run_time'>
                        <FormField name='run_time' value={draft.run_time} modify={modify_} />
                        <ErrorList errors={fieldErrors.run_time} />
                    </td>,
                    <td key='setup_time'>
                        <FormField name='setup_time' value={draft.setup_time} modify={modify_} />
                        <ErrorList errors={fieldErrors.setup_time} />
                    </td>,
                    <td key='description'>
                        <FormField name='description' value={draft.description} modify={modify_} />
                        <ErrorList errors={fieldErrors.description} />
                    </td>,
                    <td key='commentators'>
                        <FormField name='commentators' value={draft.commentators} modify={modify_} />
                        <ErrorList errors={fieldErrors.commentators} />
                    </td>,
                    <td key='buttons'>
                        <button type='button' value='Cancel' onClick={cancel_}>Cancel</button>
                        <Spinner spinning={draft._saving || false}>
                            <button type='button' value='Save' onClick={save_}>Save</button>
                        </Spinner>
                    </td>
                    ]
                    :
                    [
                    <td key='name'>
                        {connectDragPreview(<input name='name' value={speedRun.name} readOnly={true} />)}
                    </td>,
                    <td key='deprecated_runners'>
                        <input name='deprecated_runners' value={speedRun.deprecated_runners} readOnly={true} />
                    </td>,
                    <td key='console'>
                        <input name='console' value={speedRun.console} readOnly={true} />
                    </td>,
                    <td key='run_time'>
                        <input name='run_time' value={speedRun.run_time} readOnly={true} />
                    </td>,
                    <td key='setup_time'>
                        <input name='setup_time' value={speedRun.setup_time} readOnly={true} />
                    </td>,
                    <td key='description'>
                        <input name='description' value={speedRun.description} readOnly={true} />
                    </td>,
                    <td key='commentators'>
                        <input name='commentators' value={speedRun.commentators} readOnly={true} />
                    </td>,
                    <td key='buttons'>
                        <button type='button' value='Edit' onClick={edit_}>Edit</button>
                    </td>
                    ]
                }
            </tr>
        );
    }

    getChanges() {
        return _.pick(
            _.pick(this.props.draft, (value, key) => {
                return value !== (this.props.speedRun ? this.props.speedRun[key] : '');
            }),
            ['name', 'deprecated_runners', 'console', 'run_time', 'setup_time', 'description', 'commentators']
        );
    }

    modify_(field, e) {
        this.props.updateField(field, e.target.value);
    }

    legalMove_(source_pk) {
        return source_pk && this.props.speedRun.pk !== source_pk;
    }

    cancel_() {
        this.props.cancel();
    }

    save_() {
        let params = this.getChanges();
        if (Object.keys(params).length) {
            this.props.saveModel(params);
        }
    }

    edit_() {
        this.props.editModel();
    }
}

SpeedRun.propTypes = {
    connectDragSource: PropTypes.func.isRequired,
    connectDragPreview: PropTypes.func.isRequired,
    isDragging: PropTypes.bool.isRequired
};

SpeedRun = DragSource('SpeedRun', speedRunSource, function collect(connect, monitor) {
    return {
        connectDragSource: connect.dragSource(),
        connectDragPreview: connect.dragPreview(),
        isDragging: monitor.isDragging()
    }
})(SpeedRun);

class EmptyTableDropTarget extends React.Component {
    render() {
        const { isOver, canDrop, connectDropTarget } = this.props;
        const ElementType = this.props.elementType || 'span';
        return connectDropTarget(
            <ElementType
                style={{
                    backgroundColor: isOver && canDrop ? 'green' : 'inherit',
                }}
                >
                {this.props.children}
            </ElementType>
        );
    }
}

const emptyTableDropTarget = {
    drop: function(props) {
        return {action: function(pk) {
            props.moveSpeedRun(pk);
        }};
    },

    canDrop: function(props, monitor) {
        return true;
    }
};

EmptyTableDropTarget = DropTarget('SpeedRun', emptyTableDropTarget, function (connect, monitor) {
    return {
        connectDropTarget: connect.dropTarget(),
        isOver: monitor.isOver(),
        canDrop: monitor.canDrop(),
    };
})(EmptyTableDropTarget);

class SpeedRunTable extends React.Component {
    constructor(props) {
        super(props);
        this.newSpeedRun_ = this.newSpeedRun_.bind(this);
    }

    render() {
        const { drafts, moveSpeedRun, saveField } = this.props;
        const { saveModel_, editModel_, cancelEdit_, updateField_, moveSpeedRunToTop_ } = this;
        const speedRuns = [...this.props.speedRuns].sort(orderSort);
        return (
            <table className="table table-striped table-condensed small">
                <thead>
                    <tr>
                        <td colSpan="10" style={{textAlign: 'center'}}>{this.props.event ? this.props.event.name : 'All Events'}</td>
                    </tr>
                    <tr>
                        <th>Start Time</th>
                        <th>Order</th>
                        <th>Game</th>
                        <th>Runners</th>
                        <th>Console</th>
                        <th>Estimate/Run Time</th>
                        <th>Setup</th>
                        <th>Description</th>
                        <th colSpan="2">Commentators</th>
                    </tr>
                </thead>
                <tbody>
                    {speedRuns[0] && speedRuns[0].order === null ?
                        <EmptyTableDropTarget
                            elementType='tr'
                            moveSpeedRun={(pk) => saveField(speedRuns.find((sr) => sr.pk === pk), 'order', 1)}
                            >
                            <td style={{textAlign: 'center'}} colSpan='10'>
                                Drop a run here to start the schedule
                            </td>
                        </EmptyTableDropTarget>
                        :
                        null
                    }
                    {speedRuns.map((speedRun) => {
                        const { pk } = speedRun;
                        const draft = drafts[pk];
                        return (
                            [
                            (draft && draft._error) ?
                                [
                                    <tr key={`error-${pk}`}>
                                        <td colSpan='10'>
                                            {draft._error}
                                        </td>
                                    </tr>,
                                    ...(draft._fields.__all__ || []).map((error, i) =>
                                        <tr key={`error-${pk}-__all__-${i}`}>
                                            <td colSpan='10'>
                                                {error}
                                            </td>
                                        </tr>
                                    )
                                ]
                                :
                                null,
                            <SpeedRun
                                key={pk}
                                speedRun={speedRun}
                                draft={draft}
                                moveSpeedRun={moveSpeedRun}
                                saveField={saveField.bind(null, speedRun)}
                                editModel={editModel_.bind(this, speedRun)}
                                cancel={cancelEdit_.bind(this, draft)}
                                saveModel={saveModel_.bind(this, pk)}
                                updateField={updateField_.bind(this, pk)}
                                />
                            ]
                        );
                    })}
                    {Object.keys(drafts).map((pk) => {
                        if (pk >= 0) {
                            return null;
                        }
                        const draft = drafts[pk];
                        return (
                            [
                            draft._error ?
                                <tr key={`error-${pk}`}>
                                    <td colSpan='10'>
                                        {draft._error}
                                    </td>
                                </tr>
                                :
                                null,
                            <SpeedRun
                                key={pk}
                                draft={draft}
                                cancel={cancelEdit_.bind(this, draft)}
                                saveModel={saveModel_.bind(this, pk)}
                                updateField={updateField_.bind(this, pk)}
                                />
                            ]
                        );
                    })}
                </tbody>
            </table>
        );
    }

    saveModel_(pk, fields) {
        this.props.saveModel(pk, fields);
    }

    editModel_(model) {
        this.props.editModel(model);
    }

    cancelEdit_(model) {
        this.props.cancelEdit(model);
    }

    newSpeedRun_() {
        this.props.newSpeedRun();
    }

    updateField_(pk, field, value) {
        this.props.updateField(pk, field, value);
    }

}

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
        this.props.newDraftModel(_.extend({type: 'speedRun'}, model));
    }

    cancelEdit_(model) {
        this.props.deleteDraftModel(_.extend({type: 'speedRun'}, model));
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
