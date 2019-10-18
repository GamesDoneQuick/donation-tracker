import * as React from 'react';
import classNames from 'classnames';

import InputWrapper from './InputWrapper.js';
import Text from './Text';

import styles from './TextInput.mod.css';

const TextInputTypes = {
  TEXT: 'text',
  EMAIL: 'email',
  NUMBER: 'number',
};

const TextInput = (props) => {
  const {
    name,
    value,
    label,
    hint,
    placeholder,
    multiline=false,
    disabled=false,
    size=InputWrapper.Sizes.NORMAL,
    type=TextInputTypes.TEXT,
    leader,
    trailer,
    marginless=false,
    className,
    onChange, // (value: string, name?: string) => any,
    ...extraProps
  } = props;

  const Tag = multiline ? 'textarea' : 'input';

  const maxLength = props.maxLength;
  const usedLength = value ? value.length : 0;
  const invalidLength = maxLength != null && usedLength >= maxLength;

  const handleChange = React.useCallback((e) => {
    if(onChange == null) return false;
    onChange(e.target.value, name);
  }, [name]);

  return (
    <InputWrapper
        className={classNames(className, {[styles.disabled]: disabled})}
        label={label}
        name={name}
        hint={hint}
        marginless={marginless}
        leader={leader}
        trailer={trailer}
        size={size}>
      <Tag
        className={classNames(styles.input, {[styles.multiline]: multiline})}
        placeholder={placeholder}
        type={type}
        name={name}
        value={value}
        disabled={disabled}
        onChange={handleChange}
        {...extraProps}
      />
      { maxLength != null &&
        <div className={classNames(styles.lengthLimit, {[styles.invalidLength]: invalidLength})} aria-hidden>
          {usedLength} / {maxLength}
        </div>
      }
    </InputWrapper>
  );
};

TextInput.Sizes = InputWrapper.Sizes;
TextInput.Types = TextInputTypes;

export default TextInput;
