import React from 'react';

import { usePermission } from '@public/api/helpers/auth';
import APIErrorList from '@public/APIErrorList';
import { useEventFromQuery, useEventParam, useSplitRuns } from '@public/apiv2/hooks';
import { useRunsQuery } from '@public/apiv2/reducers/trackerApi';
import Spinner from '@public/spinner';

import { Speedrun } from '@admin/scheduleEditor/speedrun';

function Header({ title }: { title?: string }) {
  return (
    <thead>
      <tr>
        <td colSpan={7}>Note: All displayed times are in your local timezone, NOT the event timezone!</td>
      </tr>
      <tr>
        <th colSpan={7} style={{ textAlign: 'center' }}>
          {title}
        </th>
      </tr>
      <tr>
        <th>Start Time</th>
        <th>Order</th>
        <th>Game</th>
        <th>Category</th>
        <th>Runners</th>
        <th>Estimate/Run Time</th>
        <th>Setup</th>
      </tr>
    </thead>
  );
}
export default function ScheduleEditor() {
  const eventId = useEventParam();
  const canViewRuns = usePermission('tracker.view_speedrun');
  const queryParams = React.useMemo(() => (canViewRuns ? { all: '' } : {}), [canViewRuns]);
  const { data: runs, error: runsError, isLoading: runsLoading } = useRunsQuery({ urlParams: eventId, queryParams });
  const { event, error: eventError, isLoading: eventLoading } = useEventFromQuery(eventId);
  const [orderedRuns, unorderedRuns] = useSplitRuns(runs);

  return (
    <APIErrorList errors={[runsError, eventError]}>
      <Spinner spinning={runsLoading || eventLoading}>
        <table>
          <Header title={event?.name} />
          <tbody>
            {orderedRuns.map(r => (
              <Speedrun key={r.id} run={r} />
            ))}
            {unorderedRuns.map(r => (
              <Speedrun key={r.id} run={r} />
            ))}
          </tbody>
        </table>
      </Spinner>
    </APIErrorList>
  );
}
