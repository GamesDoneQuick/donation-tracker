import React from 'react';
import {
  Button,
  Callout,
  CalloutType,
  Clickable,
  Header,
  Interactive,
  Stack,
  Text,
  useTooltip,
} from '@faulty/gdq-design';

import { getSocketPath } from '@public/apiv2/reducers/sockets';
import { useAppSelector } from '@public/apiv2/Store';
import InfoCircle from '@uikit/icons/InfoCircle';

import styles from './ConnectionStatus.mod.css';

interface ConnectionStatusProps {
  refetch: () => unknown;
  isFetching: boolean;
}

const STATUS_CONTENT: Record<CalloutType, { heading: string; body: string }> = {
  success: {
    heading: 'Socket Connected',
    body: 'New donations will appear as they are received and automatically update whenever anyone processes them.',
  },
  warning: {
    heading: 'Socket Reconnecting',
    body: 'Attempting to reconnect.',
  },
  danger: {
    heading: 'Socket Failed',
    body: 'You can still take action on donations, but you will not see new donations in real time. Please refresh the page to reconnect.',
  },
  info: {
    heading: 'No Socket',
    body: 'Sockets are not configured.',
  },
};

export default function ConnectionStatus({ refetch, isFetching }: ConnectionStatusProps) {
  const connectionStatus = useAppSelector(state => state.sockets[getSocketPath(state, 'processing')]);

  let calloutType: CalloutType;

  switch (connectionStatus) {
    case WebSocket.OPEN:
      calloutType = 'success';
      break;
    case WebSocket.CONNECTING:
      calloutType = 'warning';
      break;
    default:
      calloutType = 'danger';
      break;
  }

  const statusContent = STATUS_CONTENT[calloutType];
  const [tooltipProps] = useTooltip<HTMLSpanElement>(
    <Text variant="text-sm/normal" className={styles.tooltip}>
      {statusContent.body}
    </Text>,
    {
      attach: 'right',
    },
  );

  return (
    <Callout type={calloutType}>
      <Stack align="stretch">
        <Header tag="h2" variant="header-sm/normal">
          {statusContent.heading}
          <Interactive as="span" className={styles.tipTrigger}>
            <Clickable as="span" {...tooltipProps}>
              <InfoCircle />
            </Clickable>
          </Interactive>
        </Header>
        {calloutType === 'danger' && <Button onPress={refetch}>{isFetching ? 'Loading' : 'Manual Fetch'}</Button>}
      </Stack>
    </Callout>
  );
}
