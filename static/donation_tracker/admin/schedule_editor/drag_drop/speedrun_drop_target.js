import React from 'react';
const { PropTypes } = React;
import { DropTarget } from 'react-dnd';

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

SpeedRunDropTarget.propTypes = {
    before: PropTypes.bool.isRequired,
    pk: PropTypes.number.isRequired,
};

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

export default SpeedRunDropTarget;
