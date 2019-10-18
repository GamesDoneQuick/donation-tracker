import * as React from 'react';
import classNames from 'classnames';

import styles from './ProgressBar.mod.css';

const ProgressBar = (props) => {
  const {
    progress,
    secondaryProgress=null,
    className
  } = props;

  return (
    <div className={classNames(styles.container, className)}>
      <div className={styles.bar} style={{
          '--progress': `${progress}%`,
        }} />
      { secondaryProgress != null
        ? <div className={classNames(styles.bar, styles.secondaryBar)} style={{
            '--progress': `${secondaryProgress}%`,
          }} />
        : null
      }
    </div>
  );
};

export default ProgressBar;
