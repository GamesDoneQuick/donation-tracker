import * as React from 'react';
import classNames from 'classnames';

import styles from './Container.mod.css';

const ContainerSizes = {
  NORMAL: styles.sizeNormal,
  WIDE: styles.sizeWide,
  FULL: styles.sizeFull,
};

type ContainerProps = {
  size?: (typeof ContainerSizes)[keyof typeof ContainerSizes];
  className?: string;
  children: React.ReactNode;
};

const Container = (props: ContainerProps) => {
  const { size = ContainerSizes.NORMAL, className, children } = props;

  return <div className={classNames(styles.container, size, className)}>{children}</div>;
};

Container.Sizes = ContainerSizes;

export default Container;
