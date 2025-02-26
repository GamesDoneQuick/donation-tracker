import React from 'react';

import Header from '@uikit/Header';
import Text from '@uikit/Text';

interface ErrorBoundaryProps extends React.PropsWithChildren {
  verbose?: boolean;
  expected?: boolean;
}

interface ErrorBoundaryState {
  error: Error | null;
}

export default class ErrorBoundary extends React.PureComponent<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { error: null };

  componentDidCatch(error: Error) {
    this.setState({ error });
  }

  render() {
    const { verbose = false, expected = false } = this.props;
    const { error } = this.state;
    if (error != null) {
      return (
        <span data-fail-test={verbose ? 'true' : null} data-fail-expected={expected ? 'true' : null} className="error">
          <Header>Something went wrong:</Header>
          <Text>{error.message}</Text>
          <pre>
            <code>{error.stack}</code>
          </pre>
        </span>
      );
    }

    return <>{this.props.children}</>;
  }
}
