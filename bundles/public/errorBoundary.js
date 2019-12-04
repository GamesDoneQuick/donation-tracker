import React from 'react';
import PropTypes from 'prop-types';

import Header from '../uikit/Header';

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

    if (error == null) return children;

    return (
      <span data-fail-test={verbose ? 'true' : null} className="error">
        <Header>Something went wrong:</Header>
        <pre>
          <code>{error.stack}</code>
        </pre>
      </span>
    );
  }
}
