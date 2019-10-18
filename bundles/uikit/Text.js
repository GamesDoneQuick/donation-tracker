import * as React from 'react';
import classNames from 'classnames';

import styles from './Text.mod.css';

const Sizes = {
  SIZE_24: styles.size24,
  SIZE_20: styles.size20,
  SIZE_16: styles.size16,
  SIZE_14: styles.size14,
  SIZE_12: styles.size12,
};

const Colors = {
  NORMAL: styles.colorNormal,
  MUTED: styles.colorMuted,
  LINK: styles.colorLink,
};

const Text = (props) => {
  const {
    size = Sizes.SIZE_16,
    color = Colors.NORMAL,
    marginless = false,
    oneline = false,
    className,
    children
  } = props;

  return (
    <p  className={classNames(
          styles.text,
          color,
          size,
          className, {
            [styles.oneline]: oneline,
            [styles.marginless]: marginless,
          }
        )}
      >
      {children}
    </p>
  )
};

Text.Sizes = Sizes;
Text.Colors = Colors;

export default Text;
