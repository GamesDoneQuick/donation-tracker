import React from 'react';
import { DateTime, IANAZone } from 'luxon';

import APIErrorList from '@public/APIErrorList';
import { usePermission } from '@public/apiv2/helpers/auth';
import { useEventFromQuery, useEventParam, useSplitRuns } from '@public/apiv2/hooks';
import { Ad, Interview } from '@public/apiv2/Models';
import { useInterviewsQuery, useLazyAdsQuery, useRunsQuery } from '@public/apiv2/reducers/trackerApi';
import Spinner from '@public/spinner';

import LastSlotDropTarget from './dragDrop/lastSlotDropTarget';
import AdRow from './AdRow';
import InterviewRow from './InterviewRow';
import { RunRow } from './RunRow';

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
  const canViewInterviews = usePermission('tracker.view_interview');
  const canViewAds = usePermission('tracker.view_ad');
  const runQueryParams = React.useMemo(() => (canViewRuns ? { all: '' } : {}), [canViewRuns]);
  const interviewQueryParams = React.useMemo(() => (canViewInterviews ? { all: '' } : {}), [canViewInterviews]);

  const {
    data: runs,
    error: runsError,
    isFetching: runsFetching,
    refetch: refetchRuns,
  } = useRunsQuery({ urlParams: eventId, queryParams: runQueryParams });
  const {
    data: interviews,
    error: interviewsError,
    isFetching: interviewsFetching,
    refetch: refetchInterviews,
  } = useInterviewsQuery({ urlParams: eventId, queryParams: interviewQueryParams });
  const [fetchAds, { data: ads, error: adsError, isFetching: adsFetching }] = useLazyAdsQuery();
  const {
    data: event,
    error: eventError,
    isFetching: eventFetching,
    refetch: refetchEvent,
  } = useEventFromQuery(eventId);
  const [orderedRuns, unorderedRuns] = useSplitRuns(runs);
  const interstitials = React.useMemo(() => {
    if (runs == null) {
      return [];
    }
    return orderedRuns.reduce(
      (interstitials, run, i, runs) => {
        const n = runs.at(i + 1);
        interstitials[run.id] = [...(ads || []), ...(interviews || [])]
          .filter(i => i.order >= run.order && (n == null || i.order < n.order))
          .sort((a, b) => a.suborder - b.suborder);
        return interstitials;
      },
      {} as Record<number, (Ad | Interview)[]>,
    );
  }, [ads, interviews, orderedRuns, runs]);
  const colSpan = canViewRuns ? 8 : 7;
  const lastTargetError = React.useCallback(
    (c: React.ReactNode) => (
      <tr>
        <td colSpan={colSpan}>{c}</td>
      </tr>
    ),
    [colSpan],
  );
  React.useEffect(() => {
    if (canViewAds && !(adsFetching || ads)) {
      fetchAds({ urlParams: eventId });
    }
  }, [ads, adsFetching, canViewAds, eventId, fetchAds]);

  const [showAds, setShowAds] = React.useState(true);
  const [showInterviews, setShowInterviews] = React.useState(true);

  const refetch = React.useCallback(() => {
    refetchRuns();
    refetchEvent();
    refetchInterviews();
    if (canViewAds) {
      fetchAds({ urlParams: eventId });
    }
  }, [canViewAds, eventId, fetchAds, refetchEvent, refetchInterviews, refetchRuns]);

  return (
    <>
      <div>
        <button disabled={runsFetching || eventFetching || interviewsFetching || adsFetching} onClick={refetch}>
          Refresh
        </button>
      </div>
      {canViewAds && (
        <div>
          <label>
            <input type="checkbox" checked={showAds} onChange={e => setShowAds(e.target.checked)} />
            Show Ads
          </label>
        </div>
      )}
      <div>
        <label>
          <input type="checkbox" checked={showInterviews} onChange={e => setShowInterviews(e.target.checked)} />
          Show Interviews
        </label>
      </div>
      <APIErrorList errors={[runsError, eventError, interviewsError, adsError]}>
        <Spinner
          spinning={runsFetching || eventFetching || interviewsFetching || adsFetching}
          showPartial={!!(event && runs)}>
          <table className="table table-striped table-condensed small">
            <Header timezone={event?.timezone} title={event?.name} />
            <tbody>
              {orderedRuns.map((r, i, runs) => (
                <React.Fragment key={r.id}>
                  <RunRow run={r} />
                  {interstitials[r.id].map(i =>
                    i.type === 'interview'
                      ? showInterviews && <InterviewRow key={i.id} interview={i} />
                      : showAds && <AdRow key={i.id} ad={i} />,
                  )}
                </React.Fragment>
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
                <RunRow key={r.id} run={r} />
              ))}
            </tbody>
          </table>
        </Spinner>
      </APIErrorList>
    </>
  );
}
