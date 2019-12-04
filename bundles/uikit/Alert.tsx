import * as React from 'react';
import classNames from 'classnames';

import Icon from './Icon';
import Text from './Text';

import styles from './Alert.mod.css';

type AlertProps = {
  className?: string;
  children: React.ReactNode;
};

const Alert = (props: AlertProps) => {
  const { className, children } = props;

  return (
    <div className={classNames(styles.container, className)}>
      <Icon className={styles.icon} name={Icon.Types.EXCLAMATION} />
      <div className={styles.content}>{children}</div>
    </div>
  );
};

export default Alert;
