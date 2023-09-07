import * as React from 'react';
import classNames from 'classnames';

import styles from './Header.mod.css';

const HeaderSizes = {
  H1: styles.size1,
  H2: styles.size2,
  H3: styles.size3,
  H4: styles.size4,
  H5: styles.size5,
  H6: styles.size6,
  HUGE: styles.sizeHuge,
};

const HeaderColors = {
  NORMAL: styles.colorNormal,
  MUTED: styles.colorMuted,
};

type HeaderProps = {
  size?: (typeof HeaderSizes)[keyof typeof HeaderSizes];
  color?: (typeof HeaderColors)[keyof typeof HeaderColors];
  marginless?: boolean;
  oneline?: boolean;
  className?: string;
  children: React.ReactNode;
};

const Header = (props: HeaderProps) => {
  const {
    size = HeaderSizes.H2,
    color = HeaderColors.NORMAL,
    marginless = false,
    oneline = false,
    className,
    children,
  } = props;

  return (
    <h1
      className={classNames(styles.header, color, size, className, {
        [styles.oneline]: oneline,
        [styles.marginless]: marginless,
      })}>
      {children}
    </h1>
  );
};

Header.Sizes = HeaderSizes;
Header.Colors = HeaderColors;

export default Header;
