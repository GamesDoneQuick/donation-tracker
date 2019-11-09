import * as React from 'react';
import classNames from 'classnames';

import * as CurrencyUtils from '../public/util/currency';
import InputWrapper, { InputWrapperPassthroughProps } from './InputWrapper';
import Text from './Text';

import styles from './CurrencyInput.mod.css';

type CurrencyInputProps = InputWrapperPassthroughProps & {
  value?: number;
  placeholder?: string;
  disabled?: boolean;
  onChange?: (value: number, name?: string) => void;
  [inputProps: string]: any;
};

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
    ...inputProps
  } = props;

  const [internalValue, setInternalValue] = React.useState(value != null ? value.toFixed(2) : '');

  React.useEffect(() => {
    const parsedValue = CurrencyUtils.parseCurrency(internalValue);
    if (parsedValue != value) {
      setInternalValue(value != null ? value.toFixed(2) : '');
    }
  }, [value, internalValue]);

  const handleChange = React.useCallback(
    e => {
      const rawValue = e.target.value;
      setInternalValue(rawValue);

      const parsedValue = CurrencyUtils.parseCurrency(rawValue);
      if (parsedValue != null && onChange != null) {
        onChange(parsedValue, name);
      }
    },
    [name, value, onChange],
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
      <input
        className={classNames(styles.input)}
        placeholder={placeholder}
        type="number"
        name={name}
        value={internalValue}
        disabled={disabled}
        onChange={handleChange}
        {...inputProps}
      />
    </InputWrapper>
  );
};

CurrencyInput.Sizes = InputWrapper.Sizes;

export default CurrencyInput;
