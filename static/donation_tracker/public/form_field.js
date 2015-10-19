import React from 'react';

let { PropTypes } = React;

class FormField extends React.Component {

    render() {
        const { name, value } = this.props;
        const onChange_ = this.onChange_.bind(this);
        return (
            <input name={name} value={value} onChange={onChange_} />
        );
    }

    onChange_(e) {
        this.props.modify(this.props.name, e.target.value);
    }
}

FormField.defaultProps = {
    value: ''
};

FormField.propTypes = {
    name: PropTypes.string.isRequired,
    value: PropTypes.string,
    modify: PropTypes.func.isRequired,
};


module.exports = FormField;
