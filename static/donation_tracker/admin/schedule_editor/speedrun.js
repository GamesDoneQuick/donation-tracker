import React from 'react';
const { PropTypes } = React;
import { DragSource } from 'react-dnd';
import _ from 'underscore';

import Spinner from '../../public/spinner';
import OrderTarget from '../../public/order_target';
import FormField from '../../public/form_field';
import ErrorList from '../../public/error_list';

import SpeedrunDropTarget from './drag_drop/speedrun_drop_target';

class Speedrun extends React.Component {
    constructor(props) {
        super(props);
        const {
            speedrun,
            draft,
            saveField,
            editModel,
            cancelEdit,
            saveModel,
            updateField,
        } = this.props;
        // bind here so that we get fewer spurious 'such and such' changed
        // TODO: Rework these so they only pass the pk and type, not the entire model...
        this.saveField = saveField && saveField.bind(null, speedrun);
        this.editModel = editModel && editModel.bind(null, speedrun);
        this.cancel = cancelEdit.bind(null, draft);
        this.saveModel = saveModel.bind(null, speedrun.pk);
        this.updateField = updateField.bind(null, speedrun.pk);
        this.legalMove_ = this.legalMove_.bind(this);
        this.save_ = this.save_.bind(this);
    }

    componentWillReceiveProps(nextProps) {
        const {
            draft,
            speedrun,
            saveField,
            editModel,
        } = this.props;
        if ((draft || {}).pk !== (nextProps.draft || {}).pk) {
            this.cancel = nextProps.cancelEdit.bind(null, nextProps.draft);
        }
        if (speedrun !== nextProps.speedrun) {
            this.saveField = saveField && saveField.bind(null, nextProps.speedrun);
            this.editModel = editModel && editModel.bind(null, nextProps.speedrun);
        }
    }

    shouldComponentUpdate(nextProps, nextState) {
        return !_.isEqual(nextProps, this.props);
    }

    line() {
        const {
            speedrun,
            draft,
            connectDragPreview
        } = this.props;
        const fieldErrors = draft ? (draft._fields || {}) : {};
        const {
            cancel,
            editModel,
            updateField,
            save_,
        } = this;
        return draft ?
            [
            <td key='name'>
                {connectDragPreview(<FormField name='name' value={draft.name} modify={updateField} />)}
                <ErrorList errors={fieldErrors.name} />
            </td>,
            <td key='deprecated_runners'>
                <FormField name='deprecated_runners' value={draft.deprecated_runners} modify={updateField} />
                <ErrorList errors={fieldErrors.deprecated_runners} />
            </td>,
            <td key='console'>
                <FormField name='console' value={draft.console} modify={updateField} />
                <ErrorList errors={fieldErrors.console} />
            </td>,
            <td key='run_time'>
                <FormField name='run_time' value={draft.run_time} modify={updateField} />
                <ErrorList errors={fieldErrors.run_time} />
            </td>,
            <td key='setup_time'>
                <FormField name='setup_time' value={draft.setup_time} modify={updateField} />
                <ErrorList errors={fieldErrors.setup_time} />
            </td>,
            <td key='description'>
                <FormField name='description' value={draft.description} modify={updateField} />
                <ErrorList errors={fieldErrors.description} />
            </td>,
            <td key='commentators'>
                <FormField name='commentators' value={draft.commentators} modify={updateField} />
                <ErrorList errors={fieldErrors.commentators} />
            </td>,
            <td key='buttons'>
                <button type='button' value='Cancel' onClick={cancel}>Cancel</button>
                <Spinner spinning={(speedrun._internal && speedrun._internal.saving) || false}>
                    <button type='button' value='Save' onClick={save_}>Save</button>
                </Spinner>
            </td>
            ]
            :
            [
            <td key='name'>
                {connectDragPreview(<input name='name' value={speedrun.name} readOnly={true} />)}
            </td>,
            <td key='deprecated_runners'>
                <input name='deprecated_runners' value={speedrun.deprecated_runners} readOnly={true} />
            </td>,
            <td key='console'>
                <input name='console' value={speedrun.console} readOnly={true} />
            </td>,
            <td key='run_time'>
                <input name='run_time' value={speedrun.run_time} readOnly={true} />
            </td>,
            <td key='setup_time'>
                <input name='setup_time' value={speedrun.setup_time} readOnly={true} />
            </td>,
            <td key='description'>
                <input name='description' value={speedrun.description} readOnly={true} />
            </td>,
            <td key='commentators'>
                <input name='commentators' value={speedrun.commentators} readOnly={true} />
            </td>,
            <td key='buttons'>
                <button type='button' value='Edit' onClick={editModel}>Edit</button>
            </td>
            ];
    }

    render() {
        const {
            speedrun,
            isDragging,
            moveSpeedrun,
            connectDragSource,
        } = this.props;
        const {
            legalMove_,
            saveField,
        } = this;
        return (
            <tr style={{opacity: isDragging ? 0.5 : 1}}>
                <td className='small'>
                    {(speedrun && speedrun.order !== null && speedrun.starttime !== null) ? dateFormat(Date.parse(speedrun.starttime)) : 'Unscheduled' }
                </td>
                <td style={{textAlign: 'center'}}>
                    <OrderTarget
                        spinning={(speedrun._internal && (speedrun._internal.moving || speedrun._internal.saving)) || false}
                        connectDragSource={connectDragSource}
                        nullOrder={saveField.bind(null, 'order', null)}
                        target={!!speedrun.order}
                        targetType={SpeedrunDropTarget}
                        targetProps={{
                            pk: speedrun.pk,
                            legalMove: legalMove_,
                            moveSpeedrun: moveSpeedrun,
                        }}
                        />
                </td>
                {this.line()}
            </tr>
        );
    }

    getChanges() {
        return _.pick(
            _.pick(this.props.draft, (value, key) => {
                return value !== (this.props.speedrun ? this.props.speedrun[key] : '');
            }),
            ['name', 'deprecated_runners', 'console', 'run_time', 'setup_time', 'description', 'commentators']
        );
    }

    legalMove_(source_pk) {
        return source_pk && this.props.speedrun.pk !== source_pk;
    }

    save_() {
        const params = this.getChanges();
        if (Object.keys(params).length) {
            this.saveModel(params);
        }
    }
}

const SpeedrunShape = PropTypes.shape({
    pk: PropTypes.number,
    name: PropTypes.string.isRequired,
    order: PropTypes.number,
    deprecated_runners: PropTypes.string.isRequired,
    //console: PropTypes.string.isRequired,
    start_time: PropTypes.string,
    end_time: PropTypes.string,
    description: PropTypes.string.isRequired,
    commentators: PropTypes.string.isRequired,
});

Speedrun.propTypes = {
    connectDragSource: PropTypes.func.isRequired,
    connectDragPreview: PropTypes.func.isRequired,
    isDragging: PropTypes.bool.isRequired,
    speedrun: SpeedrunShape.isRequired,
    draft: SpeedrunShape,
    moveSpeedrun: PropTypes.func,
    saveField: PropTypes.func,
    saveModel: PropTypes.func.isRequired,
    cancelEdit: PropTypes.func.isRequired,
    editModel: PropTypes.func.isRequired,
};

const speedrunSource = {
    beginDrag: function(props) {
        return {source_pk: props.speedrun.pk};
    },

    endDrag: function(props, monitor) {
        const result = monitor.getDropResult();
        if (result && result.action) {
            result.action(props.speedrun.pk);
        }
    },
};

Speedrun = DragSource('Speedrun', speedrunSource, function collect(connect, monitor) {
    return {
        connectDragSource: connect.dragSource(),
        connectDragPreview: connect.dragPreview(),
        isDragging: monitor.isDragging()
    }
})(Speedrun);

export default Speedrun;
