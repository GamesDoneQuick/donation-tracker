import React from 'react';
import _ from 'lodash';
import moment from 'moment';
import PropTypes from 'prop-types';
import { useDrag } from 'react-dnd';

import ErrorList from '@public/errorList';
import FormField from '@public/formField';
import OrderTarget from '@public/orderTarget';
import Spinner from '@public/spinner';

import SpeedrunDropTarget from './dragDrop/speedrunDropTarget';

class Speedrun extends React.Component {
  shouldComponentUpdate(nextProps, nextState) {
    return !_.isEqual(nextProps, this.props);
  }

  line() {
    const { speedrun, draft, connectDragPreview, editModel } = this.props;
    const fieldErrors = draft?._fields || {};
    const { cancelEdit_, editModel_, updateField_, save_ } = this;
    return draft ? (
      <React.Fragment>
        <td>
          {connectDragPreview(
            <div>
              <FormField name="name" value={draft.name} modify={updateField_} />
            </div>,
          )}
          <ErrorList errors={fieldErrors.name} />
        </td>
        <td>
          <input name="runners" value={speedrun.runners} readOnly={true} />
        </td>
        <td>
          <FormField name="console" value={draft.console} modify={updateField_} />
          <ErrorList errors={fieldErrors.console} />
        </td>
        <td>
          <FormField name="run_time" value={draft.run_time} modify={updateField_} />
          <ErrorList errors={fieldErrors.run_time} />
        </td>
        <td>
          <FormField name="setup_time" value={draft.setup_time} modify={updateField_} />
          <ErrorList errors={fieldErrors.setup_time} />
        </td>
        <td>
          <FormField name="description" value={draft.description} modify={updateField_} />
          <ErrorList errors={fieldErrors.description} />
        </td>
        <td>
          <input name="commentators" value={speedrun.commentators} readOnly={true} />
        </td>
        <td>
          <Spinner spinning={!!(speedrun._internal && speedrun._internal.saving)}>
            <button type="button" value="Cancel" onClick={cancelEdit_}>
              Cancel
            </button>
            <button type="button" value="Save" onClick={save_}>
              Save
            </button>
          </Spinner>
        </td>
      </React.Fragment>
    ) : (
      <React.Fragment>
        <td>{connectDragPreview(<input name="name" value={speedrun.name} readOnly={true} />)}</td>
        <td>
          <input name="runners" value={speedrun.runners} readOnly={true} placeholder="runners" />
        </td>
        <td>
          <input name="console" value={speedrun.console} readOnly={true} placeholder="console" />
        </td>
        <td>
          <input name="run_time" value={speedrun.run_time} readOnly={true} placeholder="run time" />
        </td>
        <td>
          <input name="setup_time" value={speedrun.setup_time} readOnly={true} placeholder="setup time" />
        </td>
        <td>
          <input name="description" value={speedrun.description} readOnly={true} placeholder="description" />
        </td>
        <td>
          <input name="commentators" value={speedrun.commentators} readOnly={true} placeholder="commentators" />
        </td>
        {editModel ? (
          <td>
            <button type="button" value="Edit" onClick={editModel_}>
              Edit
            </button>
          </td>
        ) : null}
      </React.Fragment>
    );
  }

  render() {
    const { speedrun, isDragging, moveSpeedrun, connectDragSource, saveField } = this.props;
    const { legalMove_, nullOrder_ } = this;
    const starttime =
      speedrun && speedrun.order !== null && speedrun.starttime !== null
        ? moment(speedrun.starttime).format('dddd, MMMM Do, h:mm a')
        : 'Unscheduled';
    const spinning = !!(speedrun._internal?.moving || speedrun._internal?.saving);
    const errors = speedrun._internal?.errors;
    return (
      <>
        {errors && Object.entries(errors).map(([key, errors]) => <ErrorList key={key} errors={errors} />)}
        <tr style={{ opacity: isDragging ? 0.5 : 1 }}>
          <td className="small">
            {starttime}
            {speedrun.anchor_time ? (
              <>
                <br />
                Anchored
              </>
            ) : null}
          </td>
          <td style={{ textAlign: 'center' }}>
            {moveSpeedrun ? (
              <OrderTarget
                spinning={spinning}
                connectDragSource={connectDragSource}
                nullOrder={saveField && nullOrder_}
                target={!!speedrun.order}
                targetType={SpeedrunDropTarget}
                targetProps={{
                  pk: speedrun.pk,
                  legalMove: legalMove_,
                  moveSpeedrun: moveSpeedrun,
                }}
              />
            ) : null}
          </td>
          {this.line()}
        </tr>
      </>
    );
  }

  getChanges() {
    return _.pick(
      _.pickBy(this.props.draft, (value, key) => {
        return value !== (this.props.speedrun ? this.props.speedrun[key] : '');
      }),
      ['name', 'deprecated_runners', 'console', 'run_time', 'setup_time', 'description', 'commentators'],
    );
  }

  legalMove_ = source_pk => {
    return source_pk && this.props.speedrun.pk !== source_pk;
  };

  editModel_ = () => {
    this.props.editModel(this.props.speedrun);
  };

  updateField_ = (field, value) => {
    this.props.updateField(this.props.speedrun.pk, field, value);
  };

  nullOrder_ = () => {
    this.props.moveSpeedrun(this.props.speedrun.pk, null, true);
  };

  cancelEdit_ = () => {
    this.props.cancelEdit(this.props.draft);
  };

  save_ = () => {
    const params = this.getChanges();
    if (Object.keys(params).length) {
      this.props.saveModel(this.props.speedrun.pk, params);
    }
  };
}

const SpeedrunShape = PropTypes.shape({
  pk: PropTypes.number,
  name: PropTypes.string.isRequired,
  order: PropTypes.number,
  deprecated_runners: PropTypes.string.isRequired,
  //console: PropTypes.string.isRequired,
  start_time: PropTypes.string,
  end_time: PropTypes.string,
  anchor_time: PropTypes.string,
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
  updateField: PropTypes.func,
  saveField: PropTypes.func,
  saveModel: PropTypes.func,
  cancelEdit: PropTypes.func,
  editModel: PropTypes.func,
};

export default function DraggableSpeedrun(props) {
  const [{ isDragging }, drag, preview] = useDrag(() => ({
    type: 'speedrun',
    item: { pk: props.speedrun.pk },
    endDrag(props, monitor) {
      const result = monitor.getDropResult();
      if (result && result.action) {
        result.action(props.speedrun.pk);
      }
    },
    collect: monitor => ({ isDragging: monitor.isDragging() }),
  }));

  return <Speedrun {...props} connectDragSource={drag} connectDragPreview={preview} isDragging={isDragging} />;
}
