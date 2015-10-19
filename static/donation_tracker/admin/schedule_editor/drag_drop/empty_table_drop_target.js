import React from 'react';
const { PropTypes } = React;
import { DropTarget } from 'react-dnd';

class EmptyTableDropTarget extends React.Component {
    render() {
        const { isOver, canDrop, connectDropTarget } = this.props;
        const ElementType = this.props.elementType; // needs to be uppercase or the compiler will think it's an html tag
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
