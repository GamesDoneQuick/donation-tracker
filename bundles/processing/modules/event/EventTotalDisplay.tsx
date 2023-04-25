import * as React from 'react';
import { useQuery } from 'react-query';
import { Header, Stack, Text } from '@spyrothon/sparx';

import APIClient from '@public/apiv2/APIClient';

import useEventTotalStore, { setEventTotalIfNewer } from './EventTotalStore';

const currencyFormat = Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  minimumIntegerDigits: 1,
  minimumFractionDigits: 2,
});
const numberFormat = Intl.NumberFormat('en-US', { maximumFractionDigits: 0 });

interface EventTotalDisplayProps {
  eventId: string;
}

export default function EventTotalDisplay(props: EventTotalDisplayProps) {
  const { eventId } = props;

  const { data: event, isLoading } = useQuery(
    `events.${eventId}.with_totals`,
    () => APIClient.getEvent(eventId, { totals: true }),
    {
      cacheTime: 60 * 60 * 1000,
      staleTime: 10 * 60 * 1000,
    },
  );
  const [total, donationCount] = useEventTotalStore(state => [state.total, state.donationCount]);

  React.useEffect(() => {
    if (event?.amount == null || event?.donation_count == null) return;
    // Using updatedAt = 0 here establishes that this API call should be
    // considered outdated by the first socket update.
    setEventTotalIfNewer(event.amount, event.donation_count, 1);
  }, [event]);

  return (
    <Stack direction="horizontal" justify="stretch">
      <div>
        <Header tag="h2" variant="text-sm/secondary">
          # of Donations
        </Header>
        <Text variant="header-md/normal">{isLoading ? '--' : numberFormat.format(donationCount)}</Text>
      </div>
      <div style={{ textAlign: 'right' }}>
        <Header tag="h2" variant="text-sm/secondary">
          Total Raised
        </Header>
        <Text variant="header-md/normal">{isLoading ? '--' : currencyFormat.format(total)}</Text>
      </div>
    </Stack>
  );
}
