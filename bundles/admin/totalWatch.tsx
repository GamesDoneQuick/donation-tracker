import * as React from 'react';
import cn from 'classnames';
import { produce, WritableDraft } from 'immer';
import { DateTime, Duration, Interval } from 'luxon';

import { useConstants } from '@common/Constants';
import { APIDonation as Donation, BidChild, PaginationInfo, TreeBid } from '@public/apiv2/APITypes';
import Endpoints, { BidFeed } from '@public/apiv2/Endpoints';
import { usePermission } from '@public/apiv2/helpers/auth';
import { parseTime, toInputTime } from '@public/apiv2/helpers/luxon';
import { useEventFromRoute, useEventParam, useSplitRuns } from '@public/apiv2/hooks';
import HTTPUtils from '@public/apiv2/HTTPUtils';
import { BidState, isAnchored, OrderedRun, Run } from '@public/apiv2/Models';
import { useMilestonesQuery, useRunsQuery } from '@public/apiv2/reducers/trackerApi';
import { useDateTime } from '@public/hooks/useDateTime';
import { useNow } from '@public/hooks/useNow';

function socketState(socket: WebSocket | null) {
  if (socket) {
    switch (socket.readyState) {
      case WebSocket.CONNECTING:
        return 'CONNECTING';
      case WebSocket.OPEN:
        return 'OPEN';
      case WebSocket.CLOSED:
        return 'CLOSED';
      case WebSocket.CLOSING:
        return 'CLOSING';
    }
  } else {
    return 'No Socket';
  }
}

const intervals = [5, 15, 30, 60, 180];

type IntervalData = {
  // count, amount
  previous: [number, number];
  current: [number, number];
  intervals: { [k: number]: [number, number] };
};

function starts(time: string | DateTime) {
  if (typeof time === 'string') {
    time = parseTime(time);
  }
  return `start${time < DateTime.now() ? 'ed' : 's'} ${time.toRelative()}`;
}

const percentFormat = new Intl.NumberFormat(undefined, { style: 'percent' });

function percentage(start: number, current: number, finish: number) {
  return `${percentFormat.format((current - start) / (finish - start))}`;
}

function TimeSpan({ run }: { run: OrderedRun }) {
  return <>{`${run.starttime.toFormat('cccc h:mm a')}-${run.endtime.toFormat('h:mm a')}`}</>;
}

interface State {
  // replace with RTK query
  bids: TreeBid[];
  donations: Donation[];
}

interface AddAction {
  type: 'add';
  payload: Partial<State>;
}

interface ReplaceAction {
  type: 'replace';
  payload: Partial<State>;
}

interface SocketBid {
  id: number;
  total: number;
  parent: number | null;
  name: string;
  goal: number | null;
  state: BidState;
  speedrun: number | null;
}

interface MergeBidsAction {
  type: 'merge';
  payload: SocketBid[];
}

type Action = AddAction | ReplaceAction | MergeBidsAction;

function findChild(children: BidChild[], id: number): BidChild | undefined {
  for (let i = 0; i < children.length; ++i) {
    let child = children.at(i);
    if (child == null || child.id === id) return child;
    if (!child.istarget && child.options) {
      if ((child = findChild(child.options, id))) return child;
    }
  }
}

function findBid(bids: TreeBid[], id: number) {
  let bid = bids.find(b => b.id === id);
  if (bid) {
    return bid;
  }
  for (let i = 0; i < bids.length; ++i) {
    let child: ReturnType<typeof findChild>;
    bid = bids[i];
    if (bid.options && (child = findChild(bid.options, id))) {
      return child;
    }
  }
}

function reducer(state: State, action: Action) {
  if (action.type === 'add') {
    return produce(state, state => {
      Object.entries(action.payload).forEach(([k, v]) => {
        v.forEach(m => {
          let i = -1;
          switch (k) {
            case 'bids':
              if (m.type !== 'bid') {
                throw new Error('sanity check');
              }
              i = state.bids.findIndex(r => r.id === m.id);
              if (i !== 1) {
                state.bids[i] = m;
              } else {
                state.bids.push(m);
              }
              break;
            case 'donations':
              if (m.type !== 'donation') {
                throw new Error('sanity check');
              }
              i = state.donations.findIndex(r => r.id === m.id);
              if (i !== 1) {
                state.donations[i] = m;
              } else {
                state.donations.push(m);
              }
              break;
            default:
              throw new Error('buh');
          }
        });
      });
    });
  } else if (action.type === 'replace') {
    return produce(state, state => {
      Object.entries(action.payload).forEach(([k, v]) => {
        switch (k) {
          case 'bids':
            state.bids = v as TreeBid[];
            break;
          case 'donations':
            state.donations = v as Donation[];
            break;
          default:
            throw new Error('what');
        }
      });
    });
  } else if (action.type === 'merge') {
    return produce(state, state => {
      action.payload.forEach(b => {
        const existing = findBid(state.bids, b.id) as WritableDraft<TreeBid | BidChild | undefined>;
        if (existing) {
          existing.state = b.state;
          existing.total = b.total;
          if ('chain_steps' in existing) {
            const { chain_steps, total, goal } = existing;
            if (chain_steps && goal) {
              let remaining = total - goal;
              chain_steps.forEach((s, i) => {
                chain_steps[i] = { ...chain_steps[i], total: Math.max(0, remaining) };
                remaining -= s.goal;
              });
            }
          }
        }
      });
    });
  }
  throw new Error('what');
}

function isOrdered(r?: Run): r is OrderedRun {
  return r?.order != null;
}

export default React.memo(function TotalWatch() {
  const realNow = useNow();
  const [fakeNow, setFakeNow] = React.useState<string | null>(null);
  const [now, setNow] = React.useState(realNow);
  React.useEffect(() => {
    setNow(now => {
      if (fakeNow) {
        const dt = parseTime(fakeNow);
        if (dt.isValid && !dt.equals(now)) {
          return dt;
        } else {
          return now;
        }
      } else {
        return realNow;
      }
    });
  }, [fakeNow, realNow]);
  const [{ bids, donations }, localDispatch] = React.useReducer(reducer, {
    bids: [],
    donations: [],
  });
  const eventId = useEventParam();
  const { data: event, ...eventState } = useEventFromRoute({ queryParams: { totals: '' } });
  const { data: runs, ...runState } = useRunsQuery({ urlParams: eventId }, { pollingInterval: 60000 });
  const { data: milestones, ...milestoneState } = useMilestonesQuery(
    { urlParams: eventId },
    { pollingInterval: 60000 },
  );
  const { APIV2_ROOT } = useConstants();
  const [feed, setFeed] = React.useState<BidFeed>('current');
  const canViewBids = usePermission('tracker.view_bid');
  const [feedDonations, setFeedDonations] = React.useState<Donation[]>([]);
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
  const allDonations = React.useMemo(
    () => [...feedDonations, ...donations.filter(ad => !feedDonations.some(fd => fd.id === ad.id))],
    [donations, feedDonations],
  );
  const intervalData = React.useMemo(() => {
    return allDonations.reduce(
      (intervalData, donation) => {
        const tr = parseTime(donation.timereceived);
        if (previousRunStart && tr >= previousRunStart && (!currentRunStart || tr < currentRunStart)) {
          intervalData.previous[0] += 1;
          intervalData.previous[1] += +donation.amount;
        }
        if (currentRunStart && tr >= currentRunStart) {
          intervalData.current[0] += 1;
          intervalData.current[1] += +donation.amount;
        }
        intervals.forEach(i => {
          const min = now.minus(Duration.fromObject({ minutes: i }));
          const fn = parseTime(fakeNow);
          if (fn?.isValid ? Interval.fromDateTimes(min, fn).contains(tr) : tr >= min) {
            const [c, t] = intervalData.intervals[i] || [0, 0];
            intervalData.intervals[i] = [c + 1, t + +donation.amount];
          }
        });
        return intervalData;
      },
      { previous: [0, 0], current: [0, 0], intervals: {} } as IntervalData,
    );
  }, [allDonations, currentRunStart, fakeNow, now, previousRunStart]);

  const [total, setTotal] = React.useState(0);
  React.useEffect(() => {
    if (event?.amount) {
      setTotal(event.amount);
    }
  }, [event]);
  const retry = React.useRef<number>(0);
  const [socket, setSocket] = React.useState<WebSocket | null>(null);
  const socketRef = React.useRef<WebSocket>();
  const connectWebsocket = React.useCallback(
    () =>
      new Promise<WebSocket>(resolve => {
        const socket = new WebSocket(
          `${window.location.protocol.replace('http', 'ws')}//${window.location.host}/tracker/ws/donations/`,
        );

        socket.addEventListener('open', async () => {
          localDispatch({ type: 'replace', payload: { bids: [] } });
          if (eventId) {
            const bids = (
              await HTTPUtils.get<PaginationInfo<TreeBid>>(APIV2_ROOT + Endpoints.BIDS({ eventId, feed, tree: true }))
            ).data.results;
            localDispatch({ type: 'replace', payload: { bids } });
          }
          retry.current = 0;
        });

        socket.addEventListener('error', err => {
          console.error(err);
          retry.current += 1;
        });

        socket.addEventListener('close', () => {
          if (socketRef.current === socket) {
            const delay = Math.min(Math.pow(2.0, retry.current), 32);

            setTimeout(connectWebsocket, delay * 1000);
          }
        });

        socket.addEventListener('message', ({ data }) => {
          const parsedData = JSON.parse(data);
          setTotal(parsedData.new_total as number);
          const donation: Donation = {
            id: parsedData.id,
            // states are a lie
            transactionstate: 'COMPLETED',
            readstate: 'PENDING',
            commentstate: 'PENDING',
            commentlanguage: 'un',
            pinned: false,
            currency: 'USD',
            domain: parsedData.domain,
            type: parsedData.type,
            bids: [],
            donor_name: parsedData.donor__visiblename,
            amount: parsedData.amount,
            timereceived: parsedData.timereceived,
          };
          localDispatch({ type: 'merge', payload: parsedData.bids });
          setFeedDonations(donations => donations.filter(d => d.id !== data.id).concat([donation]));
        });
        setSocket(oldSocket => {
          socketRef.current = socket;
          if (oldSocket) {
            oldSocket.close();
          }
          return socket;
        });
        resolve(socket);
      }),
    [APIV2_ROOT, eventId, feed],
  );
  const ago = React.useMemo(() => {
    // trigger only when run changes or when fakeNow changes, not every minute
    const ago = DateTime.now().minus(Duration.fromObject({ hours: 3 }));
    const fn = parseTime(fakeNow);
    const timestamps = [fn?.isValid ? fn : ago];
    if (currentRunStart) {
      timestamps.push(currentRunStart);
    }
    if (previousRunStart) {
      timestamps.push(previousRunStart);
    }
    return DateTime.min(...timestamps).toMillis();
  }, [fakeNow, currentRunStart, previousRunStart]);
  React.useEffect(() => {
    (async () => {
      await connectWebsocket();
      let pageInfo = (
        await HTTPUtils.get<PaginationInfo<Donation>>(APIV2_ROOT + Endpoints.DONATIONS(eventId), {
          time_gte: DateTime.fromMillis(ago).toISO(),
        })
      ).data;
      const donations = pageInfo.results;
      while (pageInfo.next) {
        pageInfo = (await HTTPUtils.get<PaginationInfo<Donation>>(pageInfo.next)).data;
        donations.concat(pageInfo.results);
      }
      localDispatch({ type: 'replace', payload: { donations } });
    })();
  }, [APIV2_ROOT, ago, connectWebsocket, eventId]);
  const refresh = React.useCallback(() => {
    connectWebsocket();
    eventState.refetch();
    runState.refetch();
    milestoneState.refetch();
  }, [connectWebsocket, eventState, milestoneState, runState]);

  const format = new Intl.NumberFormat([], { minimumFractionDigits: 2 });

  return (
    <>
      <div>
        Socket State: {socketState(socket)} {retry.current > 0 && `(${retry.current})`}
      </div>
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
          </select>{' '}
          Bid Feed
        </label>
      </div>
      <div>
        <button onClick={refresh}>Force Refresh</button>
      </div>
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
      {milestones?.map(milestone => {
        const ratio = (total - milestone.start) / (milestone.amount - milestone.start);
        const display = `$${format.format(total)} — ${percentage(
          0,
          Math.min(total, milestone.amount),
          milestone.amount,
        )}`;
        return (
          total / milestone.amount < 1.25 && (
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
                    flexGrow: Math.min(total, milestone.amount),
                    borderLeft: milestone.start === 0 ? '' : '1px solid black',
                    textAlign: 'right',
                    alignContent: 'center',
                    paddingRight: '10px',
                  }}>
                  {ratio >= 0.5 ? display : ''}
                </div>
                <div
                  style={{
                    backgroundColor: 'gray',
                    color: 'white',
                    flexGrow: Math.max(0, milestone.amount - total),
                    borderLeft: milestone.amount > total ? '1px dotted black' : '',
                    textAlign: 'left',
                    alignContent: 'center',
                    paddingLeft: '10px',
                  }}>
                  {ratio < 0.5 ? display : ''}
                </div>
              </div>
            </React.Fragment>
          )
        );
      })}
      {bids.map(bid => {
        const speedrun = runs?.find((r): r is OrderedRun => isOrdered(r) && bid.speedrun === r.id);
        if (bid.chain && bid.goal != null && bid.chain_goal != null && bid.chain_remaining != null && bid.chain_steps) {
          return (
            <React.Fragment key={bid.id}>
              <h3>
                {speedrun && `${speedrun.name} (${starts(speedrun.starttime)}) -- `}
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
                {bid.chain_steps?.map(step => (
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
              {bid.chain_steps.map(c => {
                return (
                  <h4 key={c.id}>
                    {c.name} ${format.format(c.total)}/${format.format(c.goal)}
                  </h4>
                );
              })}
            </React.Fragment>
          );
        } else {
          return (
            <React.Fragment key={bid.id}>
              <h3>
                {speedrun && `${speedrun.name} (${starts(speedrun.starttime)}) -- `}
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
              {/* TODO: replace with toSorted once we can upgrade Typescript */}
              {[...(bid.options || [])]
                .sort((a, b) => b.total - a.total)
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
