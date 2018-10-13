import React from 'react';

import styles from './error_list.css';

class ErrorList extends React.Component {
    render() {
        const { errors } = this.props;
        return (
            errors.length ?
                <ul className={styles['errorlist']}>
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

export default ErrorList;
