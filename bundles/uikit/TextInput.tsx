import * as React from 'react';
import classNames from 'classnames';

import InputWrapper from './InputWrapper';
import Text from './Text';

import styles from './TextInput.mod.css';

const TextInputTypes = {
  TEXT: 'text',
  EMAIL: 'email',
  NUMBER: 'number',
};

type TextInputProps = {
  size?: typeof InputWrapper.Sizes[keyof typeof InputWrapper.Sizes];
  type?: typeof TextInputTypes[keyof typeof TextInputTypes];
  name: string;
  value?: string;
  placeholder?: string;
  label?: React.ReactNode;
  hint?: React.ReactNode;
  multiline?: boolean;
  disabled?: boolean;
  leader?: React.ReactNode;
  trailer?: React.ReactNode;
  marginless?: boolean;
  className?: string;
  onChange?: (value: string, name?: string) => void;
  [inputProps: string]: any;
};

const TextInput = (props: TextInputProps) => {
  const {
    size = InputWrapper.Sizes.NORMAL,
    type = TextInputTypes.TEXT,
    name,
    value,
    placeholder,
    label,
    hint,
    multiline = false,
    disabled = false,
    leader,
    trailer,
    marginless = false,
    className,
    onChange,
    ...inputProps
  } = props;

  const Tag = multiline ? 'textarea' : 'input';

  const maxLength = props.maxLength;
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
        value={value}
        disabled={disabled}
        onChange={handleChange}
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
