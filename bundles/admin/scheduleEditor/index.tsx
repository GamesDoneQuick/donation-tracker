import React from 'react';
import { DateTime, IANAZone } from 'luxon';

import APIErrorList from '@public/APIErrorList';
import { usePermission } from '@public/apiv2/helpers/auth';
import { useEventFromQuery, useEventParam, useSplitRuns } from '@public/apiv2/hooks';
import { useRunsQuery } from '@public/apiv2/reducers/trackerApi';
import Spinner from '@public/spinner';

import LastSlotDropTarget from '@admin/scheduleEditor/dragDrop/lastSlotDropTarget';
import { Speedrun } from '@admin/scheduleEditor/speedrun';

function Header({ timezone, title }: { timezone?: string; title?: string }) {
  const sameTimezone = React.useMemo(
    () => !!timezone && IANAZone.isValidZone(timezone) && DateTime.local().zoneName === IANAZone.create(timezone).name,
    [timezone],
  );
  const canViewRuns = usePermission('tracker.view_speedrun');
  const colSpan = canViewRuns ? 8 : 7;
  return (
    <thead>
      {!sameTimezone && (
        <tr>
          <td colSpan={colSpan} className="text-danger">
            Note: All displayed times are in your local timezone, NOT the event timezone!
          </td>
        </tr>
      )}
      <tr>
        <th colSpan={colSpan} style={{ textAlign: 'center' }}>
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
        {canViewRuns && <th>Admin</th>}
      </tr>
    </thead>
  );
}

export default function ScheduleEditor() {
  const eventId = useEventParam();
  const canViewRuns = usePermission('tracker.view_speedrun');
  const canChangeRuns = usePermission('tracker.change_speedrun');
  const queryParams = React.useMemo(() => (canViewRuns ? { all: '' } : {}), [canViewRuns]);
  const {
    data: runs,
    error: runsError,
    isFetching: runsFetching,
    refetch: refetchRuns,
  } = useRunsQuery({ urlParams: eventId, queryParams });
  const {
    data: event,
    error: eventError,
    isFetching: eventFetching,
    refetch: refetchEvent,
  } = useEventFromQuery(eventId);
  const [orderedRuns, unorderedRuns] = useSplitRuns(runs);
  const colSpan = canViewRuns ? 8 : 7;
  const lastTargetError = React.useCallback(
    (c: React.ReactNode) => (
      <tr>
        <td colSpan={colSpan}>{c}</td>
      </tr>
    ),
    [colSpan],
  );

  return (
    <>
      <button
        disabled={runsFetching || eventFetching}
        onClick={() => {
          refetchRuns();
          refetchEvent();
        }}>
        Refresh
      </button>
      <APIErrorList errors={[runsError, eventError]}>
        <Spinner spinning={runsFetching || eventFetching} showPartial={!!(event && runs)}>
          <table className="table table-striped table-condensed small">
            <Header timezone={event?.timezone} title={event?.name} />
            <tbody>
              {orderedRuns.map(r => (
                <Speedrun key={r.id} run={r} />
              ))}
              {runs?.length ? (
                canChangeRuns && (
                  <LastSlotDropTarget elementType="tr" displayError={lastTargetError}>
                    <td colSpan={colSpan} style={{ textAlign: 'center' }}>
                      --The End--
                    </td>
                  </LastSlotDropTarget>
                )
              ) : (
                <tr>
                  <td colSpan={colSpan} data-testid="empty-event">
                    This event doesn&apos;t have any runs yet. {canChangeRuns && 'Add some!'}
                  </td>
                </tr>
              )}
              {unorderedRuns.map(r => (
                <Speedrun key={r.id} run={r} />
              ))}
            </tbody>
          </table>
        </Spinner>
      </APIErrorList>
    </>
  );
}
