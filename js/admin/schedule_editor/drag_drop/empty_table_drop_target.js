import React from 'react';
import PropTypes from 'prop-types';
import { DropTarget } from 'react-dnd';

class EmptyTableDropTarget extends React.Component {
    render() {
        const { isOver, canDrop, connectDropTarget } = this.props;
        return connectDropTarget(
            <this.props.elementType
                style={{
                    backgroundColor: isOver && canDrop ? 'green' : 'inherit',
                }}
                >
                {this.props.children}
            </this.props.elementType>
        );
    }
}

EmptyTableDropTarget.defaultProps = {
    elementType: 'span'
};

EmptyTableDropTarget.propTypes = {
    connectDropTarget: PropTypes.func.isRequired,
    isOver: PropTypes.bool.isRequired,
    canDrop: PropTypes.bool.isRequired,
};

const emptyTableDropTarget = {
    drop: function(props) {
        return {action: function(pk) {
            props.moveSpeedrun(pk);
        }};
    },

    canDrop: function(props, monitor) {
        return true;
    }
};

EmptyTableDropTarget = DropTarget('Speedrun', emptyTableDropTarget, function (connect, monitor) {
    return {
        connectDropTarget: connect.dropTarget(),
        isOver: monitor.isOver(),
        canDrop: monitor.canDrop(),
    };
})(EmptyTableDropTarget);

export default EmptyTableDropTarget;
