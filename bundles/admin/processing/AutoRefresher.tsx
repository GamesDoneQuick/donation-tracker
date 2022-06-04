import * as React from 'react';

import Spinner from '@public/spinner';
import Refresh from '@uikit/icons/Refresh';

import Button from './Button';
import useAnimationFrame from './useAnimationFrame';

import styles from './AutoRefresher.mod.css';

const REFETCH_INTERVAL = 2 * 60 * 1000; // 2 minutes

interface AutoRefresherProps {
  refetch: () => Promise<unknown>;
  isFetching: boolean;
}

export default function AutoRefresher({ refetch, isFetching }: AutoRefresherProps) {
  const [lastRefresh, setLastRefresh] = React.useState(() => Date.now());

  const [, forceUpdate] = React.useState({});
  useAnimationFrame(() => forceUpdate({}));

  const handleRefetch = React.useCallback(() => {
    refetch().then(() => setLastRefresh(Date.now()));
  }, [refetch]);

  React.useEffect(() => {
    const interval = setInterval(handleRefetch, REFETCH_INTERVAL);
    return () => clearInterval(interval);
  }, [handleRefetch]);

  const elapsedInterval = Date.now() - lastRefresh;
  const intervalPercentage = Math.min(100, (elapsedInterval / REFETCH_INTERVAL) * 100);

  return (
    <div className={styles.container}>
      <div className={styles.header}>Auto-Refresh</div>
      <div className={styles.progressContainer}>
        <div className={styles.progressBar} style={{ width: `${intervalPercentage}%` }} />
      </div>
      <Button className={styles.actionButton} onClick={handleRefetch} icon={isFetching ? Spinner : Refresh}>
        {isFetching ? 'Loading' : 'Refresh Now'}
      </Button>
    </div>
  );
}
