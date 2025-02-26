import * as React from 'react';
import { DateTime } from 'luxon';

import { parseTime } from '@public/apiv2/helpers/luxon';

// returns the same DateTime object so long as the numeric representation has not changed

export function useDateTime(timestamp: DateTime | string | number | null | undefined): DateTime | null {
  if (timestamp instanceof DateTime || typeof timestamp === 'string') {
    timestamp = parseTime(timestamp).toMillis();
  }
  return React.useMemo(() => (timestamp != null ? DateTime.fromMillis(timestamp as number) : null), [timestamp]);
}
