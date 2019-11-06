import * as React from 'react';
import classNames from 'classnames';

import Clickable from './Clickable';
import Icon from './Icon';

import styles from './Checkbox.mod.css';

const CheckboxLooks = {
  NORMAL: styles.lookNormal,
  DENSE: styles.lookDense,
};

type CheckboxHeaderProps = {
  className?: string;
  children: React.ReactNode;
  [headerProp: string]: any;
};

const CheckboxHeader = (props: CheckboxHeaderProps) => {
  const { children, className, ...headerProps } = props;

  return (
    <div className={classNames(styles.header, className)} {...headerProps}>
      {props.children}
    </div>
  );
};

type CheckboxProps = {
  look: typeof CheckboxLooks[keyof typeof CheckboxLooks];
  label?: React.ReactNode;
  checked: boolean;
  disabled?: boolean;
  className?: string;
  contentClassName?: string;
  children: React.ReactNode;
  onChange: (checked: boolean) => void;
};

const Checkbox = (props: CheckboxProps) => {
  const {
    checked,
    label = null,
    disabled = false,
    look = CheckboxLooks.NORMAL,
    children,
    className,
    contentClassName,
    onChange,
  } = props;

  const handleClick = React.useCallback(() => {
    onChange(!checked);
  }, [checked]);

  return (
    <Clickable
      tag="label"
      role="checkbox"
      aria-checked={!!checked}
      className={classNames(styles.container, look, className, { [styles.disabled]: disabled })}
      onClick={handleClick}>
      <Icon className={styles.check} name={checked ? Icon.Types.CHECKBOX_CHECKED : Icon.Types.CHECKBOX_OPEN} />

      <div className={classNames(styles.content, contentClassName)}>
        {label && <CheckboxHeader>{label}</CheckboxHeader>}
        {children}
      </div>
    </Clickable>
  );
};

Checkbox.Header = CheckboxHeader;
Checkbox.Looks = CheckboxLooks;

export default Checkbox;
