import React from 'react';
import cn from 'classnames';
import ReactNumeric from 'react-numeric';

import * as CurrencyUtils from '@public/util/currency';

import InputWrapper, { InputWrapperPassthroughProps } from './InputWrapper';

import styles from './CurrencyInput.mod.css';

type CurrencyInputProps = Omit<InputWrapperPassthroughProps, 'leader'> & {
  currency: string;
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
  const currencySymbol = CurrencyUtils.getCurrencySymbol(props.currency);
  const {
    size = InputWrapper.Sizes.NORMAL,
    value,
    placeholder = '0.00',
    disabled = false,
    name,
    label,
    hint,
    leader = currencySymbol,
    trailer,
    marginless = false,
    className,
    onChange,
    max,
    ...inputProps
  } = props;
  const hasMax = max == null || max === Infinity;

  const handleChange = React.useCallback(
    (event: React.ChangeEvent<HTMLInputElement>, value: number) => {
      onChange?.(value, name);
    },
    [name, onChange],
  );

  return (
    <InputWrapper
      className={cn(className, { [styles.disabled]: disabled })}
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
        // @ts-expect-error what is this type
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
