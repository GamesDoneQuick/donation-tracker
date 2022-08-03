import React from 'react';
import PropTypes from 'prop-types';
import { DropTarget } from 'react-dnd';

import Constants from '@common/Constants';

class SpeedrunDropTarget extends React.Component {
  static propTypes = {
    before: PropTypes.bool.isRequired,
    pk: PropTypes.number.isRequired,
  };

  static contextType = Constants;

  render() {
    const { before, isOver, canDrop, connectDropTarget } = this.props;
    return connectDropTarget(
      <span
        style={{
          width: '50%',
          backgroundColor: isOver && canDrop ? 'green' : 'inherit',
          float: before ? 'left' : 'right',
        }}>
        <img src={this.context.STATIC_URL + (before ? 'prev.png' : 'next.png')} alt={before ? 'previous' : 'next'} />
      </span>,
    );
  }
}

const speedrunTarget = {
  drop: function (props, monitor) {
    return {
      action: function (source_pk) {
        props.moveSpeedrun(source_pk, props.pk, props.before);
      },
    };
  },

  canDrop: function (props, monitor) {
    return props.legalMove(monitor.getItem() ? monitor.getItem().source_pk : null);
  },
};

export default DropTarget('Speedrun', speedrunTarget, function collect(connect, monitor) {
  return {
    connectDropTarget: connect.dropTarget(),
    isOver: monitor.isOver(),
    canDrop: monitor.canDrop(),
  };
})(SpeedrunDropTarget);
