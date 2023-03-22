import * as React from 'react';
import classNames from 'classnames';

import { ProcessingSocket } from '@public/apiv2/sockets/ProcessingSocket';
import Spinner from '@public/spinner';
import Refresh from '@uikit/icons/Refresh';

import Button from './Button';

import styles from './ConnectionStatus.mod.css';

interface ConnectionStatusProps {
  refetch: () => Promise<unknown>;
  isFetching: boolean;
}

const STATUS_CONTENT = {
  connected: {
    heading: 'Live Socket Connected',
    body: 'New donations will appear as they are received and automatically update whenever anyone processes them.',
  },
  disconnected: {
    heading: 'Live Socket Disconnected',
    body:
      'Connection to the socket has been lost. You can still take action on donations, but new donations will not show up automatically or update when other processors action them. Please refresh the page to reconnect.',
  },
};

export default function ConnectionStatus({ refetch, isFetching }: ConnectionStatusProps) {
  const [isConnected, setConnected] = React.useState(() => ProcessingSocket.isConnected);

  React.useEffect(() => {
    const unsubscribe = ProcessingSocket.on('connection_changed', event => {
      setConnected(event.isConnected);
    });

    return unsubscribe;
  });

  const statusContent = STATUS_CONTENT[isConnected ? 'connected' : 'disconnected'];

  return (
    <div className={styles.container}>
      <div className={classNames(styles.status)}>
        <div
          className={classNames(styles.statusDot, {
            [styles.connected]: isConnected,
            [styles.disconnected]: !isConnected,
          })}
        />
        {statusContent.heading}
      </div>
      <div className={styles.bodyText}>{statusContent.body}</div>
      <Button className={styles.actionButton} onClick={refetch} icon={isFetching ? Spinner : Refresh}>
        {isFetching ? 'Loading' : 'Force Refresh'}
      </Button>
    </div>
  );
}
