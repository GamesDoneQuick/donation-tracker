import React from 'react';
import cn from 'classnames';

import styles from './ProgressBar.mod.css';

type ProgressBarProps = {
  progress: number;
  secondaryProgress?: number;
  className?: cn.Argument;
};

const ProgressBar = (props: ProgressBarProps) => {
  const { progress, secondaryProgress = null, className } = props;

  const primaryStyle = {
    '--progress': `${progress}%`,
  } as React.CSSProperties;

  const secondaryStyle = {
    '--progress': `${secondaryProgress}%`,
  } as React.CSSProperties;

  return (
    <div className={cn(styles.container, className)}>
      <div className={styles.bar} style={primaryStyle} />
      {secondaryProgress != null ? (
        <div className={cn(styles.bar, styles.secondaryBar)} style={secondaryStyle} />
      ) : null}
    </div>
  );
};

export default ProgressBar;
