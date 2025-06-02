import React from 'react';
import cn from 'classnames';

import Clickable from './Clickable';
import Icon from './Icon';

import styles from './Checkbox.mod.css';

const CheckboxLooks = {
  NORMAL: styles.lookNormal,
  DENSE: styles.lookDense,
};

type CheckboxHeaderProps = {
  className?: cn.Argument;
  children: React.ReactNode;
  [headerProp: string]: any;
};

const CheckboxHeader = (props: CheckboxHeaderProps) => {
  const { children, className, ...headerProps } = props;

  return (
    <div className={cn(styles.header, className)} {...headerProps}>
      {children}
    </div>
  );
};

type CheckboxProps = {
  look?: (typeof CheckboxLooks)[keyof typeof CheckboxLooks];
  label?: React.ReactNode;
  name?: string;
  checked: boolean;
  disabled?: boolean;
  className?: cn.Argument;
  contentClassName?: string;
  children?: React.ReactNode;
  onChange: (checked: boolean) => void;
};

const Checkbox = (props: CheckboxProps) => {
  const {
    look = CheckboxLooks.NORMAL,
    checked,
    label = null,
    name,
    disabled = false,
    children,
    className,
    contentClassName,
    onChange,
  } = props;

  const handleClick = React.useCallback(() => {
    onChange(!checked);
  }, [checked, onChange]);

  return (
    <Clickable
      tag="label"
      role="checkbox"
      aria-checked={!!checked}
      className={cn(styles.container, look, className, { [styles.disabled]: disabled })}
      onClick={handleClick}
      data-testid={name}>
      <Icon className={styles.check} name={checked ? Icon.Types.CHECKBOX_CHECKED : Icon.Types.CHECKBOX_OPEN} />

      <div className={cn(styles.content, contentClassName)}>
        {label && <CheckboxHeader>{label}</CheckboxHeader>}
        {children}
      </div>
    </Clickable>
  );
};

Checkbox.Header = CheckboxHeader;
Checkbox.Looks = CheckboxLooks;

export default Checkbox;
