import * as React from 'react';
import classNames from 'classnames';

import styles from './Button.mod.css';

const BUTTON_COLOR_STYLES = {
  success: styles.success,
  danger: styles.danger,
  warning: styles.warning,
  default: styles.default,
};

interface ButtonProps {
  color?: keyof typeof BUTTON_COLOR_STYLES;
  icon?: React.ComponentType;
  disabled?: boolean;
  title?: string;
  className?: string;
  children: React.ReactNode;
  onClick: (event: React.MouseEvent<HTMLButtonElement>) => unknown;
}

export default function Button(props: ButtonProps) {
  const { color = 'default', icon: Icon, disabled = false, title, className, children, onClick } = props;

  return (
    <button
      className={classNames(styles.button, BUTTON_COLOR_STYLES[color], className)}
      onClick={onClick}
      disabled={disabled}
      title={title}>
      {/* @ts-expect-error Icons have bad typing from fontawesome */}
      {Icon != null ? <Icon className={styles.icon} /> : null} {children}
    </button>
  );
}
