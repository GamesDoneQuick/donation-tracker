import * as React from 'react';
import classNames from 'classnames';

import styles from './RadioGroup.mod.css';

const RadioGroupLooks = {
  INLINE: styles.lookInline,
  VERTICAL: styles.lookVertical,
  CUSTOM: styles.lookCustom,
};

type Option = {
  name: string;
  value: any;
};

type RadioItemProps = {
  option: Option;
  selected: boolean;
  onSelect: (value: any) => void;
};

const RadioItem = (props: RadioItemProps) => {
  const { option, selected, onSelect } = props;

  const handleClick = React.useCallback(
    e => {
      e.preventDefault();
      onSelect != null && onSelect(option.value);
    },
    [option.value, onSelect],
  );

  return (
    <button className={classNames(styles.radioItem, { [styles.selectedItem]: selected })} onClick={handleClick}>
      {option.name}
    </button>
  );
};

type RadioGroupProps = {
  look?: typeof RadioGroupLooks[keyof typeof RadioGroupLooks];
  options: any[];
  value: any;
  className?: string;
  children?: (props: RadioItemProps) => React.ReactElement;
  onChange?: (value: any) => void;
};

const RadioGroup = (props: RadioGroupProps) => {
  const { options, value, look = RadioGroupLooks.INLINE, onChange, children: Option = RadioItem, className } = props;

  const handleClick = React.useCallback(
    value => {
      onChange != null && onChange(value);
    },
    [onChange],
  );

  return (
    <div className={classNames(look, className)}>
      {options.map(option => (
        <Option option={option} key={option.value} selected={value === option.value} onSelect={handleClick} />
      ))}
    </div>
  );
};

RadioGroup.Looks = RadioGroupLooks;

export default RadioGroup;
