import React from 'react';

/**
 * Wrapper around useState for booleans to provide two memoized functions to set it to true and false
 * @param {boolean} initialValue - initial value, defaults to false
 */
export function useBooleanState(initialValue = false): [boolean, () => void, () => void] {
  const [value, setValue] = React.useState(initialValue);
  const setValueTrue = React.useCallback(() => setValue(true), []);
  const setValueFalse = React.useCallback(() => setValue(false), []);
  return [value, setValueTrue, setValueFalse];
}
