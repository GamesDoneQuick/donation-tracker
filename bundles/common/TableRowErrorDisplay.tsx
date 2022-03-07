import React from 'react';

import { isValidationError, ServerError, ValidationError } from './Server';

interface ErrorDisplayProps {
  error: ServerError | ValidationError;
}

export default function TableRowErrorDisplay({ error }: ErrorDisplayProps) {
  return (
    <React.Fragment>
      <tr style={{ color: 'red' }}>
        <th>Server Error</th>
        <th>{error.error}</th>
        <th>Please Refresh Page</th>
      </tr>

      {isValidationError(error)
        ? Object.entries(error.message_dict).map(([k, vs]: [string, string[]]) => (
            <tr key={k} style={{ color: 'red' }}>
              <th>{k}</th>
              {vs.map((v: string) => (
                <th key={v}>{v}</th>
              ))}
            </tr>
          ))
        : null}
    </React.Fragment>
  );
}
