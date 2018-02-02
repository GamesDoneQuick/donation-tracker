import React from 'react';

class Spinner extends React.PureComponent {
    static defaultProps = {
        imageFile: 'ajax_select/images/loading-indicator.gif',
        spinning: true
    };

    render() {
        return (
            this.props.spinning ?
                <img src={STATIC_URL + this.props.imageFile} />
                :
                (<span>
                    {this.props.children}
                </span>)
        );
    }
}

export default Spinner;
