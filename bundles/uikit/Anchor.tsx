import * as React from 'react';
import classNames from 'classnames';

import Text from './Text';

import styles from './Anchor.mod.css';

type AnchorProps = {
  href: string;
  newTab?: boolean;
  external?: boolean;
  className?: string;
  children: React.ReactNode;
};

const Anchor = (props: AnchorProps) => {
  const { children, href, newTab = false, external = false, className } = props;

  const target = newTab ? '_blank' : undefined;
  const rel = external ? 'noopener noreferrer' : undefined;

  return (
    <a className={classNames(styles.anchor, 'block-external', className)} href={href} target={target} rel={rel}>
      {children}
    </a>
  );
};

Anchor.Sizes = Text.Sizes;
Anchor.Colors = Text.Colors;

export default Anchor;
