import React from 'react';
import PropTypes from 'prop-types';
import { DropTarget } from 'react-dnd';

class EmptyTableDropTarget extends React.Component {
  render() {
    const { isOver, canDrop, connectDropTarget, elementType: Element } = this.props;
    return connectDropTarget(
      <Element
        style={{
          backgroundColor: isOver && canDrop ? 'green' : 'inherit',
        }}>
        {this.props.children}
      </Element>,
    );
  }
}

EmptyTableDropTarget.defaultProps = {
  elementType: 'span',
};

EmptyTableDropTarget.propTypes = {
  connectDropTarget: PropTypes.func.isRequired,
  isOver: PropTypes.bool.isRequired,
  canDrop: PropTypes.bool.isRequired,
  elementType: PropTypes.elementType.isRequired,
};

const emptyTableDropTarget = {
  drop: function (props) {
    return {
      action: function (pk) {
        props.moveSpeedrun(pk);
      },
    };
  },

  canDrop: function (props, monitor) {
    return true;
  },
};

export default DropTarget('Speedrun', emptyTableDropTarget, function (connect, monitor) {
  return {
    connectDropTarget: connect.dropTarget(),
    isOver: monitor.isOver(),
    canDrop: monitor.canDrop(),
  };
})(EmptyTableDropTarget);
