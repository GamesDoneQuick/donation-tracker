import * as React from 'react';
import classNames from 'classnames';

import InputWrapper, { InputWrapperPassthroughProps } from './InputWrapper';
import Text from './Text';

import styles from './TextInput.mod.css';

const TextInputTypes = {
  TEXT: 'text',
  EMAIL: 'email',
  NUMBER: 'number',
};

type TextInputProps = InputWrapperPassthroughProps & {
  type?: typeof TextInputTypes[keyof typeof TextInputTypes];
  value?: string;
  placeholder?: string;
  multiline?: boolean;
  disabled?: boolean;
  maxLength?: number;
  onChange?: (value: string, name?: string) => void;
  [inputProps: string]: any;
};

const TextInput = (props: TextInputProps) => {
  const {
    size = InputWrapper.Sizes.NORMAL,
    type = TextInputTypes.TEXT,
    value,
    placeholder,
    multiline = false,
    disabled = false,
    maxLength,
    name,
    label,
    required = false,
    hint,
    leader,
    trailer,
    marginless = false,
    className,
    onChange,
    ...inputProps
  } = props;

  const Tag = multiline ? 'textarea' : 'input';

  const usedLength = value ? value.length : 0;
  const invalidLength = maxLength != null && usedLength >= maxLength;

  const handleChange = React.useCallback(e => (onChange != null ? onChange(e.target.value, name) : false), [
    name,
    onChange,
  ]);

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
      <Tag
        className={classNames(styles.input, { [styles.multiline]: multiline })}
        placeholder={placeholder}
        type={type}
        name={name}
        id={name}
        value={value}
        required={required}
        disabled={disabled}
        onChange={handleChange}
        maxLength={maxLength}
        data-testid={name}
        {...inputProps}
      />
      {maxLength != null && (
        <div className={classNames(styles.lengthLimit, { [styles.invalidLength]: invalidLength })} aria-hidden>
          {usedLength} / {maxLength}
        </div>
      )}
    </InputWrapper>
  );
};

TextInput.Sizes = InputWrapper.Sizes;
TextInput.Types = TextInputTypes;

export default TextInput;
