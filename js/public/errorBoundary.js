import PropTypes from 'prop-types';
import React from 'react';

export default class ErrorBoundary extends React.PureComponent {
  static propTypes = {
    children: PropTypes.node,
    verbose: PropTypes.bool.isRequired,
  };

  static defaultProps = {
    verbose: false,
  };

  state = { error: null };

  componentDidCatch(error, info) {
    this.setState({ error });
  }

  render() {
    const { error } = this.state;
    const { verbose, children } = this.props;
    if (error) {
      return <span data-fail-test={verbose ? 'true' : null} className='error'>
        Something went wrong: {error.stack.split('\n').map(l => <div>{l}</div>)}
        </span>;
    }
    return <React.Fragment>{children}</React.Fragment>;
  }
}
