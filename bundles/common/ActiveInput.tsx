import React from 'react';
import cn from 'classnames';

import Spinner from '@public/spinner';

export function ActiveInput<T>({
  className,
  input: inputProps,
  initialValue,
  displayValue = initialValue,
  canEdit,
  loading,
  confirm,
  children,
}: React.PropsWithChildren<{
  className?: string;
  input: React.HTMLProps<HTMLInputElement>;
  displayValue?: string | number;
  initialValue: string | number;
  canEdit: boolean;
  loading: boolean;
  confirm: (value: string) => Promise<T>;
}>) {
  const [invalid, setInvalid] = React.useState<string | null>(null);
  const [newValue, setValue] = React.useState<string | null>(null);

  function accept(e: { preventDefault: () => void }) {
    e.preventDefault();
    if (!invalid && newValue) {
      setValue(null);
      confirm(newValue)
        .then(() => {
          setInvalid(null);
        })
        .catch(() => {
          setValue(newValue);
        });
    }
  }

  function cancel(e: { preventDefault: () => void }) {
    e.preventDefault();
    setInvalid(null);
    setValue(null);
  }

  return newValue != null ? (
    <form
      style={{ display: 'inline' }}
      onKeyDown={e => {
        if (e.key === 'Escape') {
          cancel(e);
        }
      }}
      onSubmit={accept}>
      <label>
        <input
          autoFocus
          {...inputProps}
          value={newValue}
          onChange={e => {
            setInvalid(e.target.validationMessage);
            setValue(e.target.value);
          }}
        />
        <button
          style={{ cursor: invalid ? 'not-allowed' : 'initial' }}
          className={cn('btn', 'btn-xs', 'fa', 'fa-check', { disabled: invalid })}
          data-testid="accept"
          onClick={accept}
        />
        <button className={cn('btn', 'btn-xs', 'fa', 'fa-undo')} data-testid="cancel" onClick={cancel} />
        <br />
        {invalid && <span className="text-danger">{invalid}</span>}
      </label>
    </form>
  ) : (
    <span className={className}>
      <span>{displayValue}</span>
      {children}
      {canEdit && (
        <Spinner spinning={loading}>
          <button
            className={cn('btn', 'btn-xs', 'fa', 'fa-pencil')}
            data-testid="edit"
            onClick={() => setValue(initialValue.toString())}
          />
        </Spinner>
      )}
    </span>
  );
}
