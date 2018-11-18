import React from 'react';
import PropTypes from 'prop-types';

import Spinner from './spinner';

class OrderTarget extends React.Component {
    render() {
        const {
            target,
            targetProps,
            connectDragSource,
            nullOrder,
            spinning,
        } = this.props;
        const TargetType = this.props.targetType; // needs to be uppercase or the compiler will think it's an html tag
        return (
            <Spinner spinning={spinning}>
                {connectDragSource(
                    <span style={{cursor: 'move'}}>
                    { target ?
                        [
                        <TargetType
                            key='before'
                            before={true}
                            {...targetProps}/>,
                        <TargetType
                            key='after'
                            before={false}
                            {...targetProps}/>,
                        nullOrder ?
                            <img
                                key='null'
                                src={STATIC_URL + 'admin/img/icon_deletelink.gif'}
                                onClick={nullOrder} />
                            :
                            null
                        ]
                        :
                        <img src={STATIC_URL + 'asc.png'} />
                    }
                    </span>
                )}
            </Spinner>
        );
    }
}

OrderTarget.propTypes = {
    target: PropTypes.bool.isRequired,
    targetType: PropTypes.func.isRequired,
    connectDragSource: PropTypes.func.isRequired,
    spinning: PropTypes.bool.isRequired,
};

export default OrderTarget;
