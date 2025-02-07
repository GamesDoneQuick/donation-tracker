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
    const { speedrun, connectDragPreview } = this.props;
    return (
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
        {typeof errors === 'string' ? (
          <ErrorList errors={[errors]} />
        ) : (
          errors && Object.entries(errors).map(([key, errors]) => <ErrorList key={key} errors={errors} />)
        )}
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

  legalMove_ = source_pk => {
    return source_pk && this.props.speedrun.pk !== source_pk;
  };

  nullOrder_ = () => {
    this.props.moveSpeedrun(this.props.speedrun.pk, null, true);
  };
}

const SpeedrunShape = PropTypes.shape({
  pk: PropTypes.number,
  name: PropTypes.string.isRequired,
  order: PropTypes.number,
  //console: PropTypes.string.isRequired,
  start_time: PropTypes.string,
  end_time: PropTypes.string,
  anchor_time: PropTypes.string,
  description: PropTypes.string.isRequired,
  runners: PropTypes.array.isRequired,
  commentators: PropTypes.array.isRequired,
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
    item: { pk: props.speedrun.pk, anchored: !!props.speedrun.anchor_time },
    collect: monitor => ({ isDragging: monitor.isDragging() }),
  }));

  return <Speedrun {...props} connectDragSource={drag} connectDragPreview={preview} isDragging={isDragging} />;
}
