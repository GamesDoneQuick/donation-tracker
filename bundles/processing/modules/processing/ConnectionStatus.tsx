import * as React from 'react';
import { Button, Callout, Header, Stack, Text } from '@spyrothon/sparx';

import APIClient from '@public/apiv2/APIClient';

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
      'You can still take action on donations, but you will not see new donations in real time. Please refresh the page to reconnect.',
  },
};

export default function ConnectionStatus({ refetch, isFetching }: ConnectionStatusProps) {
  const [isConnected, setConnected] = React.useState(() => APIClient.sockets.processingSocket.isConnected);

  React.useEffect(() => {
    const unsubscribe = APIClient.sockets.processingSocket.on('connection_changed', event => {
      setConnected(event.isConnected);
    });

    return unsubscribe;
  });

  const statusContent = STATUS_CONTENT[isConnected ? 'connected' : 'disconnected'];

  return (
    <Callout type={isConnected ? 'success' : 'danger'}>
      <Stack>
        <Header tag="h2" variant="header-sm/normal">
          {statusContent.heading}
        </Header>
        <Text variant="text-xs/normal">{statusContent.body}</Text>
        <Button onClick={refetch}>{isFetching ? 'Loading' : 'Force Refresh'}</Button>
      </Stack>
    </Callout>
  );
}
