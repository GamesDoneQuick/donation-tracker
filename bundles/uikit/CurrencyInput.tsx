import * as React from 'react';
import classNames from 'classnames';
import ReactNumeric from 'react-numeric';

import InputWrapper, { InputWrapperPassthroughProps } from './InputWrapper';

import styles from './CurrencyInput.mod.css';

type CurrencyInputProps = InputWrapperPassthroughProps & {
  value?: number;
  placeholder?: string;
  disabled?: boolean;
  onChange?: (value: number, name?: string) => void;
  [inputProps: string]: any;
};

// TODO: This could use improvement to better handle edge cases like:
// - deleting the whole amount after entering.
// - entering multiple decimals (Chrome allows this on number inputs, weirdly)
// - entering thousandths or beyond
// - formatting according to user's locale
const CurrencyInput = (props: CurrencyInputProps) => {
  const {
    size = InputWrapper.Sizes.NORMAL,
    value,
    placeholder = '0.00',
    disabled = false,
    name,
    label,
    hint,
    leader = '$',
    trailer,
    marginless = false,
    className,
    onChange,
    max,
    ...inputProps
  } = props;
  const hasMax = max == null || max === Infinity;

  const handleChange = React.useCallback(
    (_event: React.SyntheticEvent, value: number) => {
      onChange != null && onChange(value, name);
    },
    [name, onChange],
  );

  return (
    <InputWrapper
      className={classNames(className, { [styles.disabled]: disabled })}
      label={label}
      name={name}
      hint={hint}
      marginless={marginless}
      leader={leader}
      trailer={trailer}
      size={size}>
      <ReactNumeric
        className={styles.input}
        id={name}
        name={name}
        value={value}
        placeholder={placeholder}
        onInvalidPaste="clamp"
        minimumValue="0.00"
        maximumValue={hasMax ? Number.MAX_SAFE_INTEGER.toFixed() : max.toFixed(2)}
        onChange={handleChange}
        disabled={disabled}
        data-testid={name}
        {...inputProps}
      />
    </InputWrapper>
  );
};

CurrencyInput.Sizes = InputWrapper.Sizes;

export default CurrencyInput;
