import * as React from 'react';
import { Link } from 'react-router-dom';
import classNames from 'classnames';

import styles from './Anchor.mod.css';

type AnchorProps = {
  href: string;
  target?: string;
  rel?: string;
  className?: string;
  children: React.ReactNode;
};

const Anchor = (props: AnchorProps) => {
  const { children, className, href, ...linkProps } = props;

  const isLocal = !/(?:^[a-z][a-z0-9+.-]*:|\/\/)/.test(href);

  if (!isLocal) {
    return (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className={classNames(styles.anchor, 'block-external', className)}
        {...linkProps}>
        {children}
      </a>
    );
  }

  return (
    <Link to={href} {...linkProps} className={classNames(styles.anchor, className)}>
      {children}
    </Link>
  );
};

export default Anchor;
