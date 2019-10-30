import * as React from 'react';

type ErrorBoundaryProps = {
  verbose: boolean;
  children: React.ReactNode;
};

type ErrorBoundaryState = {
  error: Error | null;
};

export default class ErrorBoundary extends React.PureComponent<ErrorBoundaryProps, ErrorBoundaryState> {
  static defaultProps = {
    verbose: false,
  };

  state: ErrorBoundaryState = {
    error: null
  };

  componentDidCatch(error: Error | null, info: object) {
    this.setState({ error });
  }

  render() {
    const { error } = this.state;
    const { verbose, children } = this.props;
    if (error != null && error.stack != null) {
      return (
        <span data-fail-test={verbose ? 'true' : null} className='error'>
          Something went wrong: {error.stack.split('\n').map((l: string) => <div>{l}</div>)}
        </span>
      );
    }

    return (
      <React.Fragment>{children}</React.Fragment>
    );
  }
}
