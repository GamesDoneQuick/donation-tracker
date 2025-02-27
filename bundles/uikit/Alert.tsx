import React from 'react';
import cn from 'classnames';

import Icon from './Icon';

import styles from './Alert.mod.css';

type AlertProps = {
  className?: cn.Argument;
  children: React.ReactNode;
};

const Alert = (props: AlertProps) => {
  const { className, children } = props;

  return (
    <div className={cn(styles.container, className)}>
      <Icon className={styles.icon} name={Icon.Types.EXCLAMATION} />
      <div className={styles.content}>{children}</div>
    </div>
  );
};

export default Alert;
