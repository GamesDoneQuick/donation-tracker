import React from 'react';
import PropTypes from 'prop-types';

class FormField extends React.PureComponent {
  static defaultProps = {
    value: ''
  };

  static propTypes = {
    name: PropTypes.string.isRequired,
    value: PropTypes.string,
    modify: PropTypes.func.isRequired,
  };

  render() {
    const {name, value} = this.props;
    const {onChange_} = this;
    return (
      <input name={name} value={value} onChange={onChange_} placeholder={name} />
    );
  }

  onChange_ = (e) => {
    this.props.modify(this.props.name, e.target.value);
  };
}

export default FormField;
