import React from 'react';
const { PropTypes } = React;
import { DragSource } from 'react-dnd';
import _ from 'underscore';

import Spinner from '../../public/spinner';
import OrderTarget from '../../public/order_target';
import FormField from '../../public/form_field';
import ErrorList from '../../public/error_list';

import SpeedRunDropTarget from './drag_drop/speedrun_drop_target';

class SpeedRun extends React.Component {
    constructor(props) {
        super(props);
        // TODO: isEqual doesn't work if it rebinds the functions every time, so bind them once, here, and then never again
        this.legalMove_ = this.legalMove_.bind(this);
        this.cancel_ = this.cancel_.bind(this);
        this.save_ = this.save_.bind(this);
        this.edit_ = this.edit_.bind(this);
        this.modify_ = this.modify_.bind(this);
    }

    shouldComponentUpdate(nextProps, nextState) {
        return !_.isEqual(
            _.pick(nextProps, ['speedRun', 'draft', 'isDragging']),
            _.pick(this.props, ['speedRun', 'draft', 'isDragging']));
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

const SpeedRunShape = PropTypes.shape({
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

SpeedRun.propTypes = {
    connectDragSource: PropTypes.func.isRequired,
    connectDragPreview: PropTypes.func.isRequired,
    isDragging: PropTypes.bool.isRequired,
    speedRun: SpeedRunShape.isRequired,
    draft: SpeedRunShape,
    moveSpeedRun: PropTypes.func,
    saveField: PropTypes.func,
    saveModel: PropTypes.func.isRequired,
    cancel: PropTypes.func.isRequired,
    editModel: PropTypes.func.isRequired,
};

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

SpeedRun = DragSource('SpeedRun', speedRunSource, function collect(connect, monitor) {
    return {
        connectDragSource: connect.dragSource(),
        connectDragPreview: connect.dragPreview(),
        isDragging: monitor.isDragging()
    }
})(SpeedRun);

export default SpeedRun;
