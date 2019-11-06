import * as React from 'react';
import classNames from 'classnames';

import Text from './Text';

import styles from './Anchor.mod.css';

const Anchor = props => {
  const { children, href, newTab, external, ...textProps } = props;

  const target = newTab ? '_blank' : null;
  const rel = external ? 'noopener noreferrer' : null;

  return (
    <a className={classNames(styles.anchor, 'block-external')} href={href} target={target} rel={rel}>
      {children}
    </a>
  );
};

Anchor.Sizes = Text.Sizes;
Anchor.Colors = Text.Colors;

export default Anchor;
