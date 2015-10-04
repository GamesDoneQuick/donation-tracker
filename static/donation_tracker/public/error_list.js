import React from 'react';

class ErrorList extends React.Component {
    render() {
        const { errors } = this.props;
        return (
            errors.length ?
                <ul className='errorlist'>
                    {errors.map((error, i) => <li key={i}>{error}</li>)}
                </ul>
                :
                null
        );
    }
}

ErrorList.defaultProps = {
    errors: [],
};

module.exports = ErrorList;
