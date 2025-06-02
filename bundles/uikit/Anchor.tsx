import React from 'react';
import cn from 'classnames';
import { Link } from 'react-router-dom';

import styles from './Anchor.mod.css';

type AnchorProps = {
  href?: string;
  target?: string;
  rel?: string;
  className?: cn.Argument;
  children: React.ReactNode;
};

const Anchor = (props: AnchorProps) => {
  const { children, className, href = '', ...linkProps } = props;

  const isLocal = !/(?:^[a-z][a-z0-9+.-]*:|\/\/)/.test(href);

  if (!isLocal) {
    return (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className={cn(styles.anchor, 'block-external', className)}
        {...linkProps}>
        {children}
      </a>
    );
  }

  return (
    <Link to={href} {...linkProps} className={cn(styles.anchor, className)}>
      {children}
    </Link>
  );
};

export default Anchor;
