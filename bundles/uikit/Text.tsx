import React from 'react';
import cn from 'classnames';

import styles from './Text.mod.css';

const TextSizes = {
  SIZE_24: styles.size24,
  SIZE_20: styles.size20,
  SIZE_16: styles.size16,
  SIZE_14: styles.size14,
  SIZE_12: styles.size12,
};

const TextColors = {
  NORMAL: styles.colorNormal,
  MUTED: styles.colorMuted,
  LINK: styles.colorLink,
};

type TextProps = {
  size?: (typeof TextSizes)[keyof typeof TextSizes];
  color?: (typeof TextColors)[keyof typeof TextColors];
  marginless?: boolean;
  oneline?: boolean;
  className?: cn.Argument;
  children: React.ReactNode;
};

const Text = (props: TextProps) => {
  const {
    size = TextSizes.SIZE_16,
    color = TextColors.NORMAL,
    marginless = false,
    oneline = false,
    className,
    children,
  } = props;

  return (
    <div
      className={cn(styles.text, color, size, className, {
        [styles.oneline]: oneline,
        [styles.marginless]: marginless,
      })}>
      {children}
    </div>
  );
};

Text.Sizes = TextSizes;
Text.Colors = TextColors;

export default Text;
