import React from 'react';
import cn from 'classnames';

import Alert from './Alert';
import Text from './Text';

import styles from './Text.mod.css';

interface FormError {
  message: string;
  code?: string;
}

export default function ErrorAlert({
  alertClassName = styles.colorDanger,
  errors,
  textClassName = styles.colorDanger,
}: {
  alertClassName?: cn.Argument;
  errors?: (FormError | string)[];
  textClassName?: cn.Argument;
}) {
  return (
    <>
      {errors &&
        errors.map(error => {
          const message = (error as FormError).message || (error as string);
          return (
            <Alert className={alertClassName} key={message}>
              <Text className={textClassName}>{message}</Text>
            </Alert>
          );
        })}
    </>
  );
}
