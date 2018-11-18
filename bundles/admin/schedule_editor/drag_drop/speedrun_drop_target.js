import React from 'react';
import PropTypes from 'prop-types';
import { DropTarget } from 'react-dnd';

class SpeedrunDropTarget extends React.Component {
    static propTypes = {
        before: PropTypes.bool.isRequired,
        pk: PropTypes.number.isRequired,
    };

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

const speedrunTarget = {
    drop: function(props, monitor) {
        return {
            action: function(source_pk) {
                props.moveSpeedrun(source_pk, props.pk, props.before);
            }
        };
    },

    canDrop: function(props, monitor) {
        return props.legalMove(monitor.getItem() ? monitor.getItem().source_pk : null);
    },
};

SpeedrunDropTarget = DropTarget('Speedrun', speedrunTarget, function collect(connect, monitor) {
    return {
        connectDropTarget: connect.dropTarget(),
        isOver: monitor.isOver(),
        canDrop: monitor.canDrop(),
    };
})(SpeedrunDropTarget);

export default SpeedrunDropTarget;
