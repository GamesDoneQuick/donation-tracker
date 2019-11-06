import * as React from 'react';
import classNames from 'classnames';

import styles from './Header.mod.css';

const Sizes = {
  H1: styles.size1,
  H2: styles.size2,
  H3: styles.size3,
  H4: styles.size4,
  H5: styles.size5,
  H6: styles.size6,
  HUGE: styles.sizeHuge,
};

const Colors = {
  NORMAL: styles.colorNormal,
  MUTED: styles.colorMuted,
};

const Header = props => {
  const { size = Sizes.H2, color = Colors.NORMAL, marginless = false, oneline = false, className, children } = props;

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

Header.Sizes = Sizes;
Header.Colors = Colors;

export default Header;
