import React from 'react';
import cn from 'classnames';

import { APIError, RecursiveRecord } from '@public/apiv2/reducers/trackerBaseApi';
import { concat } from '@public/util/reduce';
import { MaybeArray } from '@public/util/Types';

import Alert from './Alert';
import Text from './Text';

import styles from './Text.mod.css';

interface FormError {
  message: string;
  code?: string;
}

function extractValues(errors: MaybeArray<APIError | FormError | string> | RecursiveRecord): string[] {
  if (errors == null) {
    return [];
  } else if (typeof errors === 'string') {
    return [errors];
  } else if (Array.isArray(errors)) {
    return errors.map(e => extractValues(e)).reduce(concat, []);
  } else if ('status' in errors && errors.status === 400) {
    return extractValues(errors.data as RecursiveRecord);
  } else if ('message' in errors && typeof errors.message === 'string') {
    return [errors.message];
  } else {
    return Object.values(errors).map(extractValues).reduce(concat, []);
  }
}

export default function ErrorAlert({
  alertClassName = styles.colorDanger,
  errors,
  textClassName = styles.colorDanger,
}: {
  alertClassName?: cn.Argument;
  errors: MaybeArray<APIError | FormError | string> | RecursiveRecord;
  textClassName?: cn.Argument;
}) {
  return (
    <>
      {extractValues(errors).map(error => (
        <Alert className={alertClassName} key={error}>
          <Text className={textClassName}>{error}</Text>
        </Alert>
      ))}
    </>
  );
}
