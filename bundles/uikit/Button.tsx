import * as React from 'react';
import classNames from 'classnames';

import styles from './Button.mod.css';

const ButtonColors = {
  PRIMARY: styles.colorPrimary,
};

const ButtonLooks = {
  FILLED: styles.lookFilled,
  OUTLINED: styles.lookOutlined,
};

const ButtonSizes = {
  SMALL: styles.sizeSmall,
  NORMAL: styles.sizeNormal,
  LARGE: styles.sizeLarge,
};

type ButtonProps = {
  color: typeof ButtonColors[keyof typeof ButtonColors];
  size: typeof ButtonSizes[keyof typeof ButtonSizes];
  look: typeof ButtonLooks[keyof typeof ButtonLooks];
  fullwidth?: boolean;
  disabled?: boolean;
  className?: string;
  children: React.ReactNode;
  onClick?: () => void;
};

const Button = (props: ButtonProps) => {
  const {
    color = ButtonColors.PRIMARY,
    size = ButtonSizes.NORMAL,
    look = ButtonLooks.FILLED,
    fullwidth,
    disabled = false,
    children,
    onClick,
    className,
    ...extraProps
  } = props;

  const handleClick = React.useCallback(
    e => {
      e.preventDefault();
      if (!disabled && onClick != null) onClick();
      return false;
    },
    [disabled, onClick],
  );

  return (
    <button
      {...extraProps}
      onClick={handleClick}
      disabled={disabled}
      className={classNames(styles.button, color, size, look, className, {
        [styles.isFullwidth]: fullwidth,
      })}>
      {children}
    </button>
  );
};

Button.Colors = ButtonColors;
Button.Looks = ButtonLooks;
Button.Sizes = ButtonSizes;

export default Button;
