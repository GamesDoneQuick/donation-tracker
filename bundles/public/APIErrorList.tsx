import React from 'react';
import cn from 'classnames';
import { SerializedError } from '@reduxjs/toolkit';

import { APIError } from '@public/apiv2/reducers/trackerApi';
import { forceArray, MaybeArray } from '@public/util/Types';

import styles from '@public/errorList.mod.css';

function extractValues(d: any): string[] {
  if (typeof d === 'string') {
    return [d];
  } else if (Array.isArray(d)) {
    return d.reduce((a, n) => [...a, ...extractValues(n)], []);
  } else if (typeof d === 'object') {
    return Object.values(d).reduce((a: string[], n: any) => [...a, ...extractValues(n)], []);
  } else {
    return [d.toString()];
  }
}

function ErrorDetail({ e }: { e: APIError | SerializedError }) {
  const [expanded, setExpanded] = React.useState(false);
  if ('statusText' in e || 'data' in e || 'status' in e) {
    return (
      <>
        {expanded && (
          <button
            className={cn('btn', 'btn-xs', 'fa', 'fa-caret-down')}
            onClick={e => {
              e.preventDefault();
              setExpanded(false);
            }}
          />
        )}
        <span data-testid="detail" style={expanded ? {} : { display: 'none' }}>
          {e.statusText ?? `Code: ${e.status}`}
          <br />
          {e.data && JSON.stringify(e.data)}
        </span>
        <span data-testid="human" style={expanded ? { display: 'none' } : {}}>
          {e.data
            ? extractValues(e.data).map((d, i) => (
                <React.Fragment key={i}>
                  {i > 0 && <br />}
                  {d}
                </React.Fragment>
              ))
            : (e.statusText ?? `Code: ${e.status}`)}
        </span>
        {!expanded && (
          <button
            className={cn('btn', 'btn-xs', 'fa', 'fa-info')}
            onClick={e => {
              e.preventDefault();
              setExpanded(true);
            }}
          />
        )}
      </>
    );
  } else if ('message' in e) {
    return <>{e.message}</>;
  } else {
    // shouldn't ever happen, but who knows
    return <>{JSON.stringify(e)}</>;
  }
}

export default function APIErrorList({
  errors,
  children,
  reset,
}: React.PropsWithChildren<{
  errors?: MaybeArray<APIError | SerializedError | undefined>;
  canHide?: boolean;
  reset?: () => void;
}>) {
  const errorList = React.useMemo(() => forceArray(errors), [errors]);
  return errorList.length ? (
    <span data-testid="api-errors">
      {reset != null && (
        <button
          className={cn('btn', 'btn-xs', 'fa', 'fa-times', 'text-danger')}
          data-testid="reset"
          onClick={e => {
            e.preventDefault();
            reset();
          }}
        />
      )}
      Errors while performing operation:
      <ul className={styles.errorlist}>
        {errorList.map((e, i) => (
          <li key={i}>
            <ErrorDetail e={e} />
          </li>
        ))}
      </ul>
    </span>
  ) : (
    <>{children}</>
  );
}
