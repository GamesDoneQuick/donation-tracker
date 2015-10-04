import React from 'react';

let Spinner = React.createClass({
    getDefaultProps: function() {
        return {
            imageFile: 'ajax_select/images/loading-indicator.gif',
            spinning: true
        };
    },
    render: function() {
        return (
            this.props.spinning ?
                <img src={STATIC_URL + this.props.imageFile} />
                :
                (<span>
                    {this.props.children}
                </span>)
        );
    }
});

module.exports = Spinner;
