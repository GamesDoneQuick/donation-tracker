import React from 'react';
import { SerializedError } from '@reduxjs/toolkit';

import { APIError } from '@public/apiv2/reducers/trackerApi';
import { forceArray, MaybeArray } from '@public/util/Types';

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
  const errorList = forceArray(errors);
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
