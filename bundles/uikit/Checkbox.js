import * as React from 'react';
import classNames from 'classnames';

import Clickable from './Clickable';
import Icon from './Icon';

import styles from './Checkbox.mod.css';

const CheckboxLooks = {
  NORMAL: styles.lookNormal,
  DENSE: styles.lookDense,
};

const CheckboxHeader = (props) => {
  const {
    children,
    className,
    ...headerProps
  } = props;

  return (
    <div className={classNames(styles.header, className)} {...headerProps}>
      {props.children}
    </div>
  );
};

const Checkbox = (props) => {
  const {
    name,
    checked,
    label=null,
    disabled=false,
    look=CheckboxLooks.NORMAL,
    children,
    className,
    contentClassName,
    onChange,
  } = props;

  return (
    <Clickable
        tag="label"
        role="checkbox"
        aria-checked={!!checked}
        className={classNames(styles.container, look, className, {[styles.disabled]: disabled})}
        onClick={onChange}>
      <Icon
        className={styles.check}
        name={checked ? Icon.Types.CHECKBOX_CHECKED : Icon.Types.CHECKBOX_OPEN}
      />

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
