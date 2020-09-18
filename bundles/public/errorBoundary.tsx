import React, { useState } from 'react';

import Header from '../uikit/Header';
import Text from '../uikit/Text';

interface ErrorBoundaryInternalProps {
  onError: (error: Error) => void;
}

class ErrorBoundaryInternal extends React.PureComponent<ErrorBoundaryInternalProps> {
  componentDidCatch(error: Error) {
    this.props.onError(error);
  }

  render() {
    return this.props.children;
  }
}

export default function ErrorBoundary({ children, verbose = false }: { children: React.ReactNode; verbose?: boolean }) {
  const [error, setError] = useState<Error | null>(null);

  return (
    <ErrorBoundaryInternal onError={setError}>
      {error == null ? (
        children
      ) : (
        <span data-fail-test={verbose ? 'true' : null} className="error">
          <Header>Something went wrong:</Header>
          <Text>{error.message}</Text>
          <pre>
            <code>{error.stack}</code>
          </pre>
        </span>
      )}
    </ErrorBoundaryInternal>
  );
}
