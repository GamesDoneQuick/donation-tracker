import * as React from 'react';
import cn from 'classnames';
import { DateTime, Duration, Interval } from 'luxon';

import APIErrorList from '@public/APIErrorList';
import { BidFeed } from '@public/apiv2/Endpoints';
import { parseTime, toInputTime } from '@public/apiv2/helpers/luxon';
import {
  useAllDonationsInfiniteQuery,
  useBidTreeQuery,
  useEventFromRoute,
  useEventParam,
  useInfinitePages,
  useMilestonesQuery,
  usePermission,
  useRunsQuery,
  useSplitRuns,
} from '@public/apiv2/hooks';
import { DonationDomain, isAnchored, OrderedRun } from '@public/apiv2/Models';
import { getSocketPath } from '@public/apiv2/reducers/sockets';
import { useAppSelector } from '@public/apiv2/Store';
import { useDateTime } from '@public/hooks/useDateTime';
import { useNow } from '@public/hooks/useNow';
import Spinner from '@public/spinner';
import { sum } from '@public/util/reduce';

const intervals = [5, 15, 30, 60, 180];

type IntervalData = {
  // count, amount
  previous: [number, number];
  current: [number, number];
  intervals: { [k: number]: [number, number] };
};

function starts(time: string | DateTime, now: DateTime | null) {
  now = now ?? DateTime.now();
  time = parseTime(time);
  return `start${time < now ? 'ed' : 's'} ${time.toRelative({ base: now })}`;
}

const percentFormat = new Intl.NumberFormat(undefined, { style: 'percent' });

function percentage(start: number, current: number, finish: number) {
  return `${percentFormat.format((current - start) / (finish - start))}`;
}

function TimeSpan({ run }: { run: OrderedRun }) {
  return <>{`${run.starttime.toFormat('cccc h:mm a')}-${run.endtime.toFormat('h:mm a')}`}</>;
}

export default React.memo(function TotalWatch() {
  const realNow = useNow();
  const [fakeNow, setFakeNow] = React.useState<string | null>(null);
  const now = useDateTime(fakeNow ?? realNow);
  const [feed, setFeed] = React.useState<BidFeed>('current');
  const eventId = useEventParam();
  const { data: event, ...eventState } = useEventFromRoute({ queryParams: { totals: '' }, listen: true });
  const { data: runs, ...runState } = useRunsQuery({ urlParams: eventId }, { pollingInterval: 60000 });
  const { data: bids, ...bidState } = useBidTreeQuery({ urlParams: { eventId, feed }, listen: true });
  const { data: milestones, ...milestoneState } = useMilestonesQuery(
    { urlParams: eventId },
    { pollingInterval: 300000 },
  );
  const canViewBids = usePermission('tracker.view_bid');
  const [orderedRuns] = useSplitRuns(runs);
  const currentRun = React.useMemo(
    () => orderedRuns.find(r => Interval.fromDateTimes(r.starttime, r.endtime).contains(now)),
    [now, orderedRuns],
  );
  const currentRunStart = useDateTime(currentRun?.starttime);
  const previousRun = React.useMemo(() => orderedRuns.filter(r => now > r.endtime).at(-1), [now, orderedRuns]);
  const previousRunStart = useDateTime(previousRun?.starttime);
  const nextCheckpoint = React.useMemo(() => {
    if (currentRun) {
      const nextAnchor = orderedRuns.find(r => isAnchored(r) && r.order > currentRun.order);
      if (nextAnchor) {
        return orderedRuns.find(r => r.order === nextAnchor.order - 1);
      }
    }
  }, [currentRun, orderedRuns]);

  const [ago, setAgo] = React.useState<DateTime | null>(null);
  React.useEffect(() => {
    setAgo(ago => {
      // don't set until we at least have a list of runs, even if said list is empty
      if (runs == null) {
        return ago;
      }
      const fn = parseTime(fakeNow);
      const timestamps = [(fn?.isValid ? fn : now).minus(Duration.fromObject({ hours: 3 }))];
      if (currentRunStart) {
        timestamps.push(currentRunStart);
      }
      if (previousRunStart) {
        timestamps.push(previousRunStart);
      }
      const min = DateTime.min(...timestamps);
      // only trigger a refetch if our window somehow gets bigger
      return ago && ago < min ? ago : min;
    });
  }, [fakeNow, currentRunStart, previousRunStart, now, runs]);
  const { data: donationPages, ...donationsState } = useAllDonationsInfiniteQuery(
    {
      urlParams: { eventId },
      queryParams: ago ? { time_gte: ago.toISO() } : {},
      listen: true,
    },
    { skip: ago == null },
  );
  const donations = useInfinitePages(donationPages?.pages);
  React.useEffect(() => {
    if (donationsState.hasNextPage && !donationsState.isError) {
      donationsState.fetchNextPage();
    }
  }, [donationsState]);

  const intervalData = React.useMemo(() => {
    const intervalData: IntervalData = { previous: [0, 0], current: [0, 0], intervals: {} };
    return (donations ?? []).reduce((intervalData, donation) => {
      if (
        previousRunStart &&
        donation.timereceived >= previousRunStart &&
        (!currentRunStart || donation.timereceived < currentRunStart)
      ) {
        intervalData.previous[0] += 1;
        intervalData.previous[1] += +donation.amount;
      }
      if (currentRunStart && donation.timereceived >= currentRunStart) {
        intervalData.current[0] += 1;
        intervalData.current[1] += +donation.amount;
      }
      intervals.forEach(i => {
        const min = now.minus(Duration.fromObject({ minutes: i }));
        if (Interval.fromDateTimes(min, now).contains(donation.timereceived)) {
          const [c, t] = intervalData.intervals[i] ?? [0, 0];
          intervalData.intervals[i] = [c + 1, t + +donation.amount];
        }
      });
      return intervalData;
    }, intervalData);
  }, [donations, currentRunStart, now, previousRunStart]);
  const domainData = React.useMemo(() => {
    const total = donations.map(d => d.amount).reduce(sum, 0);
    return donations.reduce(
      (domains, donation) => {
        domains[donation.domain] = domains[donation.domain] || [0, 0, 0];
        domains[donation.domain][0] += donation.amount;
        domains[donation.domain][1] = domains[donation.domain][0] / total;
        domains[donation.domain][2] += donation.bids.map(b => b.amount).reduce(sum, 0);
        return domains;
      },
      {} as Record<DonationDomain, [number, number, number]>,
    );
  }, [donations]);

  // convenience so we don't have to keep typechecking event amount
  const total = React.useMemo(() => event?.donation_total ?? 0, [event]);

  const refresh = React.useCallback(() => {
    eventState.refetch();
    runState.refetch();
    milestoneState.refetch();
    donationsState.refetch();
    bidState.refetch();
    setAgo(now);
  }, [donationsState, eventState, milestoneState, runState, bidState, now]);
  const isConnected = useAppSelector(state => state.sockets[getSocketPath(state, 'processing')] === WebSocket.OPEN);

  const format = new Intl.NumberFormat([], { minimumFractionDigits: 2 });

  return (
    <>
      <div>Socket State: {isConnected ? 'CONNECTED' : 'CONNECTING'}</div>
      <div>
        <label>
          Time Override
          <input
            style={{ opacity: fakeNow ? 1 : 0.5 }}
            type="datetime-local"
            value={toInputTime(fakeNow || now)}
            onChange={e => setFakeNow(e.target.value)}
          />
          <button className={cn('fa', 'fa-times')} onClick={() => setFakeNow(null)} />
        </label>
      </div>
      <div>
        <label>
          <select value={feed} onChange={e => setFeed(e.target.value as BidFeed)}>
            <option value="current">Current</option>
            <option value="open">Open</option>
            <option value="public">{canViewBids ? 'Public' : 'All'}</option>
            {canViewBids && <option value="all">All</option>}
          </select>
          Bid Feed
        </label>
      </div>
      <div>
        <button onClick={refresh}>Refresh</button>
      </div>
      <Spinner
        spinning={
          donationsState.isFetching ||
          eventState.isLoading ||
          runState.isLoading ||
          milestoneState.isLoading ||
          bidState.isLoading
        }
      />
      <APIErrorList
        errors={[donationsState.error, eventState.error, runState.error, milestoneState.error, bidState.error]}
      />
      {total !== 0 && <h2>Total: ${format.format(total)}</h2>}
      {nextCheckpoint && (
        <h3>
          Next Checkpoint: <TimeSpan run={nextCheckpoint} /> ({nextCheckpoint.endtime.toRelative()}){' '}
          {nextCheckpoint.setup_time.shiftTo('minutes').minutes} minute(s)
        </h3>
      )}
      {currentRun && (
        <>
          <h3>
            Current Run: {currentRun.name} - <TimeSpan run={currentRun} />
          </h3>
          <h4>
            Total since run start: ${format.format(intervalData.current[1])} ({intervalData.current[0]})
          </h4>
        </>
      )}
      {previousRun && (
        <>
          <h4 style={{ fontSize: 18 }}>
            Total during previous run: ${format.format(intervalData.previous[1])} ({intervalData.previous[0]})
          </h4>
        </>
      )}
      {Object.entries(intervalData.intervals).map(([k, v]) => (
        <h4 key={k}>
          Total in the last {k} minutes: ${format.format(v[1])} ({v[0]})
        </h4>
      ))}
      {Object.entries(domainData).map(([domain, [total, pct, bidTotal]]) => (
        <h4 key={domain}>
          {domain}: ${format.format(total)} ({Math.floor(pct * 100)}%) (Allocated:{' '}
          {Math.floor((bidTotal / total) * 100)}%)
        </h4>
      ))}
      {event?.donation_total != null &&
        milestones?.map(milestone => {
          const ratio = (total - milestone.start) / (milestone.amount - milestone.start);
          const display = `$${format.format(total)} — ${percentage(
            0,
            Math.min(total, milestone.amount),
            milestone.amount,
          )}`;
          return (
            (total - milestone.start) / (milestone.amount - milestone.start) < 1.25 && (
              <React.Fragment key={`milestone-${milestone.id}`}>
                <h3>
                  {`${milestone.name} ${milestone.start ? `$${format.format(milestone.start)}–` : ''}$${format.format(
                    milestone.amount,
                  )}`}
                </h3>
                <div style={{ display: 'flex', width: '80%', height: 40, border: '1px solid black' }}>
                  <div style={{ backgroundColor: '#3fff00', flexBasis: milestone.start === 0 ? 0 : '10%' }} />
                  <div
                    style={{
                      backgroundColor: '#00aeef',
                      flexGrow: Math.max(0, Math.min(total - milestone.start, milestone.amount - milestone.start)),
                      borderLeft: milestone.start === 0 ? '' : '1px solid black',
                      textAlign: 'right',
                      alignContent: 'center',
                    }}>
                    {ratio >= 0.5 ? <span style={{ paddingRight: 10 }}>{display}</span> : ''}
                  </div>
                  <div
                    style={{
                      backgroundColor: 'gray',
                      color: 'white',
                      flexGrow: Math.max(0, milestone.amount - total),
                      borderLeft: milestone.amount > total ? '1px dotted black' : '',
                      textAlign: 'left',
                      alignContent: 'center',
                    }}>
                    {ratio < 0.5 ? <span style={{ paddingLeft: 10 }}>{display}</span> : ''}
                  </div>
                </div>
              </React.Fragment>
            )
          );
        })}
      {bids?.map(bid => {
        const run = orderedRuns.find(r => bid.speedrun === r.id);
        if (bid.chain && bid.goal != null && bid.chain_goal != null && bid.chain_remaining != null && bid.chain_steps) {
          return (
            <React.Fragment key={bid.id}>
              <h3>
                {run && `${run.name} (${starts(run.starttime, now)}) -- `}
                {bid.name} ${format.format(bid.total)}
                {`/$${format.format(bid.chain_goal + bid.chain_remaining)}`} ({bid.state})
              </h3>
              <div style={{ display: 'flex', width: '80%', height: 40, border: '1px solid black' }}>
                <div style={{ backgroundColor: '#00aeef', flexGrow: Math.min(bid.goal, bid.total) }} />
                <div
                  style={{
                    backgroundColor: 'gray',
                    flexGrow: Math.max(0, bid.goal - bid.total),
                    borderLeft: bid.goal > bid.total && bid.total > 0 ? '1px dotted black' : '',
                  }}
                />
                {bid.chain_steps.map(step => (
                  <React.Fragment key={step.id}>
                    <div
                      style={{
                        backgroundColor: '#00aeef',
                        flexGrow: Math.min(step.goal, step.total),
                        borderLeft: '1px solid black',
                      }}
                    />
                    <div
                      style={{
                        backgroundColor: 'gray',
                        flexGrow: Math.max(0, step.goal - step.total),
                        borderLeft: step.goal > step.total && step.total > 0 ? '1px dotted black' : '',
                      }}
                    />
                  </React.Fragment>
                ))}
              </div>
              <h4 key={bid.id}>
                {bid.name} ${format.format(bid.total)}/${format.format(bid.goal)}
              </h4>
              {bid.chain_steps.map(c => (
                <h4 key={c.id}>
                  {c.name} ${format.format(c.total)}/${format.format(c.goal)}
                </h4>
              ))}
            </React.Fragment>
          );
        } else {
          return (
            <React.Fragment key={bid.id}>
              <h3>
                {run && `${run.name} (${starts(run.starttime, now)}) -- `}
                {bid.name} ${format.format(bid.total)}
                {bid.goal ? `/$${format.format(bid.goal)}` : ''} ({bid.state})
              </h3>
              {bid.goal != null && (
                <div
                  style={{
                    display: 'flex',
                    width: '80%',
                    height: 40,
                    border: '1px solid black',
                  }}>
                  <div style={{ backgroundColor: '#00aeef', flexGrow: Math.min(bid.goal, bid.total) }} />
                  <div
                    style={{
                      backgroundColor: 'gray',
                      flexGrow: Math.max(0, bid.goal - bid.total),
                      borderLeft: bid.goal > bid.total && bid.total > 0 ? '1px dotted black' : '',
                    }}
                  />
                </div>
              )}
              {bid.options
                ?.toSorted((a, b) => b.total - a.total)
                .map(o => (
                  <h4 key={o.id}>
                    {o.name} ${format.format(o.total)} {bid.allowuseroptions && `(${o.state})`}
                  </h4>
                ))}
            </React.Fragment>
          );
        }
      })}
    </>
  );
});
