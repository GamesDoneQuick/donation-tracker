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

function APIErrorDetail({ error }: { error: APIError }) {
  const [expanded, setExpanded] = React.useState(false);
  const human = React.useMemo(() => {
    if ('statusText' in error || 'data' in error || 'status' in error) {
      if (error.status == null || error.status < 500) {
        return error.data
          ? extractValues(error.data).map((d, i) => (
              <React.Fragment key={i}>
                {i > 0 && <br />}
                {d}
              </React.Fragment>
            ))
          : (error.statusText ?? `Code: ${error.status ?? 'unknown'}`);
      } else {
        // don't display server errors because they can be an avalanche of HTML depending on which part failed
        return error.statusText ?? `Code: ${error.status ?? 'unknown'}`;
      }
    } else {
      return null;
    }
  }, [error]);
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
        {error.statusText ?? `Code: ${error.status}`}
        <br />
        {error.data ? JSON.stringify(error.data) : 'unknown'}
      </span>
      <span data-testid="human" style={expanded ? { display: 'none' } : {}}>
        {human}
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
}

const ErrorDetail = React.memo(function ErrorDetail({ error }: { error: APIError | SerializedError }) {
  if ('statusText' in error || 'data' in error || 'status' in error) {
    return <APIErrorDetail error={error} />;
  } else if ('message' in error) {
    return <>{error.message}</>;
  } else {
    return <>Unknown Error, please report this as a bug: {JSON.stringify(error)}</>;
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
            <ErrorDetail error={e} />
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
    // allows passing an inline array as the prop without triggering spurious re-renders
    setErrorList(errorList => {
      const newList = forceArray(props.errors);
      return shallowEqual(errorList, newList) ? errorList : newList;
    });
  }, [props.errors]);
  return <InternalList {...props} errors={errorList} />;
}
