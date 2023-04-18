import * as React from 'react';

import { useUserPreferencesStore } from './UserPreferencesStore';

const timeFormatter = new Intl.RelativeTimeFormat('en', { style: 'narrow' });

const UPDATE_INTERVAL = 5 * 1000;

function getRelativeTimeString(diff: number, formatter: Intl.RelativeTimeFormat) {
  if (diff > -5) {
    return 'just now';
  } else if (diff <= -4000) {
    return formatter.format(Math.round(diff / 3600), 'hours');
  } else if (diff <= -90) {
    return formatter.format(Math.round(diff / 60), 'minutes');
  } else {
    return formatter.format(Math.round(diff), 'seconds');
  }
}

interface RelativeTimeProps {
  time: Date;
  now?: Date;
  formatter?: Intl.RelativeTimeFormat;
}

export default function RelativeTime(props: RelativeTimeProps) {
  const { time, now, formatter = timeFormatter } = props;

  const useRelativeTimestamps = useUserPreferencesStore(state => state.useRelativeTimestamps);

  const diff = -((now ?? new Date()).getTime() - time.getTime()) / 1000;
  const [timeString, setTimeString] = React.useState(() => getRelativeTimeString(diff, formatter));

  React.useEffect(() => {
    if (!useRelativeTimestamps) return;

    function update() {
      const realNow = now ?? new Date();
      const diff = -(realNow.getTime() - time.getTime()) / 1000;
      setTimeString(getRelativeTimeString(diff, formatter));
    }

    const intervalId = setInterval(update, UPDATE_INTERVAL);
    return () => clearInterval(intervalId);
  }, [time, now, formatter, useRelativeTimestamps]);

  return <>{useRelativeTimestamps ? timeString : time.toLocaleString()}</>;
}
