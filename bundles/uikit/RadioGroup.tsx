import React from 'react';
import cn from 'classnames';

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
    (e: React.MouseEvent) => {
      e.preventDefault();
      onSelect?.(option.value);
    },
    [option.value, onSelect],
  );

  return (
    <button className={cn(styles.radioItem, { [styles.selectedItem]: selected })} onClick={handleClick}>
      {option.name}
    </button>
  );
};

type RadioGroupProps = {
  look?: (typeof RadioGroupLooks)[keyof typeof RadioGroupLooks];
  options: any[];
  value: any;
  className?: cn.Argument;
  children?: (props: RadioItemProps) => React.ReactElement;
  onChange?: (value: any) => void;
};

const RadioGroup = (props: RadioGroupProps) => {
  const { options, value, look = RadioGroupLooks.INLINE, onChange, children: Option = RadioItem, className } = props;

  const handleClick = React.useCallback(
    (value: any) => {
      onChange?.(value);
    },
    [onChange],
  );

  return (
    <div className={cn(look, className)}>
      {options.map(option => (
        <Option option={option} key={option.value} selected={value === option.value} onSelect={handleClick} />
      ))}
    </div>
  );
};

RadioGroup.Looks = RadioGroupLooks;

export default RadioGroup;
