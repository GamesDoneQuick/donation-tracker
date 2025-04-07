import React from 'react';
import { Header, Stack, Text } from '@faulty/gdq-design';

import { useEventFromRoute } from '@public/apiv2/hooks';
import * as CurrencyUtils from '@public/util/currency';

const numberFormat = Intl.NumberFormat('en-US', { maximumFractionDigits: 0 });

export default function EventTotalDisplay() {
  const { data: event } = useEventFromRoute({ queryParams: { totals: '' }, listen: true });

  return (
    <Stack direction="horizontal" justify="stretch">
      <div>
        <Header tag="h2" variant="text-sm/secondary">
          # of Donations
        </Header>
        <Text variant="header-md/normal">
          {event?.donation_count == null ? '--' : numberFormat.format(event?.donation_count)}
        </Text>
      </div>
      <div style={{ textAlign: 'right' }}>
        <Header tag="h2" variant="text-sm/secondary">
          Total Raised
        </Header>
        <Text variant="header-md/normal">
          {event?.amount == null
            ? '--'
            : CurrencyUtils.asCurrency(event?.amount, {
                currency: event?.paypalcurrency ?? 'USD',
              })}
        </Text>
      </div>
    </Stack>
  );
}
