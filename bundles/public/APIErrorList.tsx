import React from 'react';
import cn from 'classnames';
import { shallowEqual } from 'react-redux';
import { SerializedError } from '@reduxjs/toolkit';

import { APIError } from '@public/apiv2/reducers/trackerBaseApi';
import { concat } from '@public/util/reduce';
import { forceArray, MaybeArray } from '@public/util/Types';

import styles from '@public/errorList.mod.css';

function extractValues(d: unknown): string[] {
  if (d == null) {
    return [];
  } else if (Array.isArray(d)) {
    return d.map(extractValues).reduce(concat, []);
  } else if (typeof d === 'object') {
    return extractValues(Object.values(d));
  } else {
    return [d.toString()];
  }
}

const ErrorDetail = React.memo(function ErrorDetail({ e }: { e: APIError | SerializedError }) {
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
          {e.data ? JSON.stringify(e.data) : 'unknown'}
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
});

type ErrorListProps = React.PropsWithChildren<{
  errors?: MaybeArray<APIError | SerializedError | null | undefined>;
  reset?: () => void;
  textClass?: cn.Argument;
  listClass?: cn.Argument;
}>;

const InternalList = React.memo(function InternalList({
  errors,
  children,
  reset,
  textClass = 'text-danger',
  listClass = styles.errorlist,
}: Omit<ErrorListProps, 'errors'> & { errors: Array<APIError | SerializedError> }) {
  return errors.length ? (
    <span data-testid="api-errors">
      {reset != null && (
        <button
          className={cn('btn', 'btn-xs', 'fa', 'fa-times', textClass)}
          data-testid="reset"
          onClick={e => {
            e.preventDefault();
            reset();
          }}
        />
      )}
      <span className={cn(textClass)}>Errors while performing operation:</span>
      <ul className={cn(listClass)}>
        {errors.map((e, i) => (
          <li key={i}>
            <ErrorDetail e={e} />
          </li>
        ))}
      </ul>
    </span>
  ) : (
    <>{children}</>
  );
});

export default function APIErrorList(props: ErrorListProps) {
  const [errorList, setErrorList] = React.useState<Array<APIError | SerializedError>>([]);
  React.useEffect(() => {
    setErrorList(errorList => {
      const newList = forceArray(props.errors);
      return shallowEqual(errorList, newList) ? errorList : newList;
    });
  }, [props.errors]);
  return <InternalList {...props} errors={errorList} />;
}
