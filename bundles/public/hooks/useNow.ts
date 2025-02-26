import React from 'react';
import { DateTime } from 'luxon';

export function useNow(interval: number | false = 60000) {
  const [now, setNow] = React.useState(DateTime.now());
  React.useEffect(() => {
    if (interval !== false) {
      const refresh = setInterval(() => setNow(DateTime.now()), interval);
      return () => {
        clearInterval(refresh);
      };
    }
  }, [interval]);
  return now;
}
