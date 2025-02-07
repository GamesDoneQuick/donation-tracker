import React from 'react';
import { SerializedError } from '@reduxjs/toolkit';

import { APIError } from '@public/apiv2/reducers/trackerApi';

type MaybeArray<T> = T | T[];

function ErrorDetail({ e }: { e: APIError | SerializedError }) {
  if ('statusText' in e || 'data' in e || 'status' in e) {
    return (
      <>
        {e.statusText ?? e.status}
        <br />
        {e.data && JSON.stringify(e.data)}
      </>
    );
  } else if ('message' in e) {
    return <>{e.message}</>;
  } else {
    // shouldn't ever happen, but who knows
    return <>{e}</>;
  }
}

export default function APIErrorList({
  errors,
  children,
}: React.PropsWithChildren<{ errors?: MaybeArray<APIError | SerializedError | undefined> }>) {
  let errorList: (APIError | SerializedError)[];
  if (Array.isArray(errors)) {
    errorList = errors.filter((e): e is APIError => !!e);
  } else {
    errorList = errors ? [errors] : [];
  }
  return errorList.length ? (
    <ul>
      Errors while fetching data:
      {errorList.map((e, i) => (
        <li key={i}>
          <ErrorDetail e={e} />
        </li>
      ))}
    </ul>
  ) : (
    <>{children}</>
  );
}
