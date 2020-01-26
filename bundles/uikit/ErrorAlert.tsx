import React from 'react';
import Alert from './Alert';
import Text from './Text';

interface FormError {
  message: string;
  code?: string;
}

export default function ErrorAlert({ errors }: { errors?: (FormError | string)[] }) {
  return (
    <>
      {errors &&
        errors.map(error => {
          const message = (error as FormError).message || (error as string);
          return (
            <Alert key={message}>
              <Text>{message}</Text>
            </Alert>
          );
        })}
    </>
  );
}
