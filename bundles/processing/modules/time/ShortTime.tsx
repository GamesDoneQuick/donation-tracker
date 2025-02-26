import React from 'react';
import { DateTime } from 'luxon';

import { useNow } from '@public/hooks/useNow';

export default function ShortTime({ now: fakeNow, time }: { now?: DateTime; time: DateTime }) {
  const realNow = useNow();
  const now = fakeNow ?? realNow;
  return <>{time.toLocaleString(now.hasSame(time, 'day') ? DateTime.TIME_SIMPLE : DateTime.DATETIME_SHORT)}</>;
}
