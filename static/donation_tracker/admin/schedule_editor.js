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
    if (a.order < b.order) {
        return -1;
    } else {
        return 1;
    }
}

class SubmissionDropTarget extends React.Component {
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

let submissionTarget = {
    drop: function(props) {
        return _.pick(props, ['pk', 'before']);
    },

    canDrop: function(props, monitor) {
        return props.legalMove(monitor.getItem() ? monitor.getItem().source_pk : null);
    },
};

SubmissionDropTarget = DropTarget('Submission', submissionTarget, function collect(connect, monitor) {
    return {
        connectDropTarget: connect.dropTarget(),
        isOver: monitor.isOver(),
        canDrop: monitor.canDrop(),
    };
})(SubmissionDropTarget);

let submissionSource = {
    beginDrag: function(props) {
        return {source_pk: props.submission.pk};
    },

    endDrag: function(props, monitor) {
        const result = monitor.getDropResult();
        if (result) {
            props.moveSubmission(props.submission.pk, result.pk, result.before);
        }
    },
};

class Submission extends React.Component {
    constructor(props) {
        super(props);
        this.legalMove_ = this.legalMove_.bind(this);
        this.cancel_ = this.cancel_.bind(this);
        this.save_ = this.save_.bind(this);
        this.edit_ = this.edit_.bind(this);
        this.modify_ = this.modify_.bind(this);
    }

    render() {
        const { submission, draft, isDragging, connectDragSource, connectDragPreview } = this.props;
        const fieldErrors = draft ? (draft._fields || {}) : {};
        const { legalMove_, cancel_, save_, edit_, modify_ } = this;
        return (
            <tr style={{opacity: isDragging ? 0.5 : 1}}>
                <td className='small'>
                    {submission ? dateFormat(Date.parse(submission.start_time)) : '---' }
                </td>
                <td style={{textAlign: 'center'}}>
                    {submission ?
                        <Spinner spinning={(draft && draft._saving) || false}>
                            {connectDragSource(
                                <span style={{cursor: 'move'}}>
                                    <SubmissionDropTarget
                                        pk={submission.pk}
                                        before={true}
                                        legalMove={legalMove_} />
                                    <SubmissionDropTarget
                                        pk={submission.pk}
                                        before={false}
                                        legalMove={legalMove_} />
                                </span>
                            )}
                        </Spinner>
                            :
                        null
                    }
                </td>,
                {draft ?
                    [
                    <td key='name'>
                        {connectDragPreview(<input name='name' value={draft.name} onChange={modify_.bind(this, 'name')} />)}
                        <ErrorList errors={fieldErrors.name} />
                    </td>,
                    <td key='console'>
                        <FormField name='console' value={draft.console} modify={this.modify_} />
                        <ErrorList errors={fieldErrors.console} />
                    </td>,
                    <td key='estimate'>
                        <input name='estimate' value={draft.estimate} onChange={modify_.bind(this, 'estimate')}/>
                        <ErrorList errors={fieldErrors.estimate} />
                    </td>,
                    <td key='setup'>
                        <input name='setup' value={draft.setup} onChange={modify_.bind(this, 'setup')}/>
                        <ErrorList errors={fieldErrors.setup} />
                    </td>,
                    <td key='comments'>
                        <input name='comments' value={draft.comments} onChange={modify_.bind(this, 'comments')}/>
                        <ErrorList errors={fieldErrors.comments} />
                    </td>,
                    <td key='commentators'>
                        <input name='commentators' value={draft.commentators} onChange={modify_.bind(this, 'commentators')}/>
                        <ErrorList errors={fieldErrors.commentators} />
                    </td>,
                    <td key='category'>
                        <input name='category' value={draft.category} onChange={modify_.bind(this, 'category')}/>
                        <ErrorList errors={fieldErrors.category} />
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
                        {connectDragPreview(<input name='name' value={submission.name} readOnly={true} />)}
                    </td>,
                    <td key='console'>
                        <input name='console' value={submission.console} readOnly={true} />
                    </td>,
                    <td key='estimate'>
                        <input name='estimate' value={submission.estimate} readOnly={true} />
                    </td>,
                    <td key='setup'>
                        <input name='setup' value={submission.setup} readOnly={true} />
                    </td>,
                    <td key='comments'>
                        <input name='comments' value={submission.comments} readOnly={true} />
                    </td>,
                    <td key='commentators'>
                        <input name='commentators' value={submission.commentators} readOnly={true} />
                    </td>,
                    <td key='category'>
                        <input name='category' value={submission.category} readOnly={true} />
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
                return value !== (this.props.submission ? this.props.submission[key] : '');
            }),
            ['name', 'console', 'estimate', 'setup', 'comments', 'commentators', 'category']
        );
    }

    modify_(field, e) {
        this.props.updateField(field, e.target.value);
    }

    legalMove_(source_pk) {
        return source_pk && this.props.submission.pk !== source_pk;
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

Submission.propTypes = {
    connectDragSource: PropTypes.func.isRequired,
    connectDragPreview: PropTypes.func.isRequired,
    isDragging: PropTypes.bool.isRequired
};

Submission = DragSource('Submission', submissionSource, function collect(connect, monitor) {
    return {
        connectDragSource: connect.dragSource(),
        connectDragPreview: connect.dragPreview(),
        isDragging: monitor.isDragging()
    }
})(Submission);

class SubmissionTable extends React.Component {
    constructor(props) {
        super(props);
        this.newSubmission_ = this.newSubmission_.bind(this);
    }

    render() {
        const { submissions, drafts, moveSubmission } = this.props;
        const { saveModel_, editModel_, cancelEdit_, newSubmission_, updateField_ } = this;
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
                    <th>Console</th>
                    <th>Estimate</th>
                    <th>Setup</th>
                    <th>Comments</th>
                    <th>Commentators</th>
                    <th colSpan="2">Category</th>
                </tr>
                </thead>
                <tbody>
                {submissions.map((submission) => {
                    const { pk } = submission;
                    const draft = drafts[pk];
                    return (
                        [
                        (draft && draft._error) ?
                            <tr key={`error-${pk}`}>
                                <td colSpan='10'>
                                    {draft._error}
                                </td>
                            </tr>
                            :
                            null,
                        <Submission
                            key={pk}
                            submission={submission}
                            draft={draft}
                            moveSubmission={moveSubmission}
                            editModel={editModel_.bind(this, submission)}
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
                        <Submission
                            key={pk}
                            draft={draft}
                            cancel={cancelEdit_.bind(this, draft)}
                            saveModel={saveModel_.bind(this, pk)}
                            updateField={updateField_.bind(this, pk)}
                            />
                        ]
                    );
                })}
                <tr>
                    <td colSpan="10" style={{textAlign: 'center'}}><button type='button' value='New Submission' onClick={newSubmission_}>New Submission</button></td>
                </tr>
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

    newSubmission_() {
        this.props.newSubmission();
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
        this.newSubmission_ = this.newSubmission_.bind(this);
        this.updateField_ = this.updateField_.bind(this);
    }

    render() {
        const { submissions, events, drafts, status, moveSubmission } = this.props;
        const { event } = this.props.params;
        const { saveModel_, editModel_, cancelEdit_, newSubmission_, moveSubmission_, updateField_ } = this;
        const loading = status.submission === 'loading' || status.event === 'loading';
        return (
            <Spinner spinning={loading}>
                {(status.submission === 'success' ?
                    <SubmissionTable event={event ? _.findWhere(events, {pk: parseInt(event)}) : null}
                                     drafts={drafts}
                                     submissions={submissions}
                                     saveModel={saveModel_}
                                     editModel={editModel_}
                                     cancelEdit={cancelEdit_}
                                     newSubmission={newSubmission_}
                                     moveSubmission={moveSubmission}
                                     updateField={updateField_} />
                    : null)}
            </Spinner>
        );
    }

    componentWillReceiveProps(newProps) {
        if (this.props.params.event !== newProps.params.event) {
            this.refreshSubmissions_(newProps.params.event);
        }
    }

    componentWillMount() {
        this.refreshSubmissions_(this.props.params.event);
    }

    refreshSubmissions_(event) {
        const { status } = this.props;
        if (status.submission !== 'loading' && status.submission !== 'success') {
            this.props.loadModels(
                'submission',
                {event: event, all: 1},
                orderSort
            );
        }
        if (status.event !== 'loading' && status.event !== 'success') {
            this.props.loadModels('event');
        }
    }

    saveModel_(pk, fields) {
        this.props.saveDraftModels([{type: 'submission', pk, fields}], orderSort);
    }

    editModel_(model) {
        this.props.newDraftModel(_.extend({type: 'submission'}, model));
    }

    cancelEdit_(model) {
        this.props.deleteDraftModel(_.extend({type: 'submission'}, model));
    }

    newSubmission_() {
        this.props.newDraftModel({type: 'submission'});
    }

    updateField_(pk, field, value) {
        this.props.updateDraftModelField('submission', pk, field, value);
    }
}

function select(state) {
    const { models, drafts, status } = state;
    const { events, submissions } = models;
    return {
        events,
        submissions,
        status,
        drafts: drafts.submissions || {},
    };
}

function dispatch(dispatch) {
    return {
        loadModels: (model, params, compare, additive) => {
            dispatch(actions.models.loadModels(model, params, compare, additive));
        },
        moveSubmission: (source, destination, before) => {
            dispatch(actions.models.command({
                    command: 'MoveSubmission',
                    moving: source,
                    other: destination,
                    before: before ? 1 : 0,
                }, orderSort))
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
        saveDraftModels: (models, compare) => {
            dispatch(actions.models.saveDraftModels(models, compare));
        },
    };
}

ScheduleEditor = connect(select, dispatch)(ScheduleEditor);

module.exports = ScheduleEditor;
