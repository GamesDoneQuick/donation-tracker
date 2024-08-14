import * as React from 'react';
import { produce } from 'immer';
import { DateTime, Duration, Interval } from 'luxon';
import { useParams } from 'react-router';

import { useConstants } from '@common/Constants';
import { usePermission } from '@public/api/helpers/auth';
import useSafeDispatch from '@public/api/useDispatch';
import { BidFeed, parseDuration } from '@public/apiv2/actions/models';
import {
  APIBid as Bid,
  APIDonation as Donation,
  APIEvent as Event,
  APIMilestone as Milestone,
  APIRun as Run,
  BidChain,
  BidChild,
  PaginationInfo,
} from '@public/apiv2/APITypes';
import Endpoints from '@public/apiv2/Endpoints';
import HTTPUtils from '@public/apiv2/HTTPUtils';
import { BidState } from '@public/apiv2/Models';

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
  if (!(time instanceof DateTime)) {
    time = iso(time);
  }
  return `start${time < DateTime.now() ? 'ed' : 's'} ${time.toRelative()}`;
}

const percentFormat = new Intl.NumberFormat(undefined, { style: 'percent' });

function percentage(start: number, current: number, finish: number) {
  return `${percentFormat.format((current - start) / (finish - start))}`;
}

function TimeSpan({ run }: { run: OrderedRun }) {
  return (
    <>
      {`${DateTime.fromISO(run.starttime).toFormat('cccc h:mm a')}-${DateTime.fromISO(run.endtime).toFormat('h:mm a')}`}
    </>
  );
}

function useNow(interval = 60000) {
  const [now, setNow] = React.useState(DateTime.now());
  React.useEffect(() => {
    const refresh = setInterval(() => setNow(DateTime.now()), interval);
    return () => {
      clearInterval(refresh);
    };
  }, [interval]);
  return now;
}

// caching
function useTimestamp(timestamp: DateTime | string | number | null | undefined) {
  if (timestamp instanceof DateTime) {
    timestamp = timestamp.toMillis();
  } else if (typeof timestamp === 'string') {
    timestamp = iso(timestamp).toMillis();
  }
  return React.useMemo(() => timestamp && DateTime.fromMillis(timestamp as number), [timestamp]);
}

// replace with RTK query

interface State {
  events: Event[];
  runs: Run[];
  bids: (Bid & { total: number })[];
  donations: Donation[];
  milestones: Milestone[];
}

interface AddAction {
  type: 'add';
  payload: Partial<State>;
}

interface ReplaceAction {
  type: 'replace';
  payload: Partial<State>;
}

interface RemoveAction {
  type: 'remove';
  payload: { type: 'event' | 'speedrun' | 'bid' | 'donation'; id: number }[];
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

function removeById<T extends { type: string; id: number }>(m: T[], a: { type: string; id: number }[]) {
  return m.filter(m => a.find(a => m.id === a.id && m.type === a.type) == null);
}

type Action = AddAction | RemoveAction | ReplaceAction | MergeBidsAction;

function findChild(children: BidChild[], id: number): BidChild | undefined {
  for (let i = 0; i < children.length; ++i) {
    let child: BidChild | undefined = children[i];
    if (child.id === id) return child;
    if (!child.istarget && child.options) {
      child = findChild(child.options, id);
      if (child) return child;
    }
  }
}

function findBid(bids: Bid[], id: number): ((Bid | BidChild) & { total: number }) | undefined {
  let bid: Bid | undefined = bids.find(b => b.id === id);
  if (bid) {
    return bid;
  }
  for (let i = 0; i < bids.length; ++i) {
    let child: BidChild | undefined;
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
            case 'events':
              if (m.type !== 'event') {
                throw new Error('sanity check');
              }
              i = state.events.findIndex(e => e.id === m.id);
              if (i !== 1) {
                state.events[i] = m;
              } else {
                state.events.push(m);
              }
              break;
            case 'runs':
              if (m.type !== 'speedrun') {
                throw new Error('sanity check');
              }
              i = state.runs.findIndex(r => r.id === m.id);
              if (i !== 1) {
                state.runs[i] = m;
              } else {
                state.runs.push(m);
              }
              break;
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
          case 'events':
            state.events = v as Event[];
            break;
          case 'bids':
            state.bids = v as Bid[];
            break;
          case 'runs':
            state.runs = v as Run[];
            break;
          case 'donations':
            state.donations = v as Donation[];
            break;
          case 'milestones':
            state.milestones = v as Milestone[];
            break;
          default:
            throw new Error('what');
        }
      });
    });
  } else if (action.type === 'remove') {
    return produce(state, state => {
      state.donations = removeById(state.donations, action.payload);
      state.events = removeById(state.events, action.payload);
      state.runs = removeById(state.runs, action.payload);
      state.bids = removeById(state.bids, action.payload);
    });
  } else if (action.type === 'merge') {
    return produce(state, state => {
      action.payload.forEach(b => {
        const existing = findBid(state.bids, b.id);
        if (existing) {
          existing.state = b.state;
          existing.total = b.total;
          const e = existing as Bid;
          if (e.chain_steps) {
            let remaining = e.total - e.goal!;
            e.chain_steps.forEach((s: BidChain & { total: number }) => {
              s.total = Math.max(0, remaining);
              remaining -= s.goal;
            });
          }
        }
      });
    });
  }
  throw new Error('what');
}

const iso = DateTime.fromISO;

function n(n?: string) {
  return n != null ? +n : n;
}

interface OrderedRun extends Run {
  starttime: string;
  endtime: string;
  order: number;
}

function isOrdered(r?: Run): r is OrderedRun {
  return r?.order != null;
}

export default React.memo(function TotalWatch() {
  const now = useNow();
  const eventId = n(useParams<{ eventId: string }>().eventId);
  const [{ events, bids, runs, donations, milestones }, localDispatch] = React.useReducer(reducer, {
    events: [],
    bids: [],
    runs: [],
    donations: [],
    milestones: [],
  });
  const event = events.find(e => eventId && e.id === eventId);
  const { APIV2_ROOT } = useConstants();
  const [feed, setFeed] = React.useState<BidFeed>('current');
  const canViewBids = usePermission('tracker.view_bid');
  const [feedDonations, setFeedDonations] = React.useState<Donation[]>([]);
  const currentRun = React.useMemo(
    () =>
      runs?.find(
        (r): r is OrderedRun => isOrdered(r) && Interval.fromDateTimes(iso(r.starttime), iso(r.endtime)).contains(now),
      ),
    [now, runs],
  );
  const currentRunStart = useTimestamp(currentRun?.starttime);
  const previousRun = React.useMemo(
    () => runs?.filter(r => r.endtime && now > iso(r.endtime)).slice(-1)?.[0],
    [now, runs],
  );
  const previousRunStart = useTimestamp(previousRun?.starttime);
  const nextCheckpoint: OrderedRun | undefined = React.useMemo(() => {
    const nextAnchor = runs?.find<OrderedRun>(
      (r): r is OrderedRun => isOrdered(r) && r.anchor_time != null && now < iso(r.anchor_time),
    );
    if (isOrdered(nextAnchor)) {
      return runs?.find<OrderedRun>((r): r is OrderedRun => isOrdered(r) && r.order === nextAnchor.order - 1);
    }
  }, [now, runs]);
  const allDonations = React.useMemo(
    () => [...feedDonations, ...donations.filter(ad => !feedDonations.some(fd => fd.id === ad.id))],
    [donations, feedDonations],
  );
  const intervalData = React.useMemo(() => {
    return allDonations.reduce(
      (intervalData, donation) => {
        const tr = iso(donation.timereceived);
        if (previousRunStart && tr >= previousRunStart && (!currentRunStart || tr < currentRunStart)) {
          intervalData.previous[0] += 1;
          intervalData.previous[1] += +donation.amount;
        }
        if (currentRunStart && tr >= currentRunStart) {
          intervalData.current[0] += 1;
          intervalData.current[1] += +donation.amount;
        }
        intervals.forEach(i => {
          if (tr >= now.minus(Duration.fromObject({ minutes: i }))) {
            const [c, t] = intervalData.intervals[i] || [0, 0];
            intervalData.intervals[i] = [c + 1, t + +donation.amount];
          }
        });
        return intervalData;
      },
      { previous: [0, 0], current: [0, 0], intervals: {} } as IntervalData,
    );
  }, [allDonations, currentRunStart, now, previousRunStart]);

  const [total, setTotal] = React.useState(0);
  React.useEffect(() => {
    if (event?.amount) {
      setTotal(event.amount);
    }
  }, [event]);
  const dispatch = useSafeDispatch();
  const fetchRuns = React.useCallback(() => {
    (async () => {
      const runs = await HTTPUtils.get<PaginationInfo<Run>>(Endpoints.RUNS(eventId));
      localDispatch({ type: 'replace', payload: { runs: runs.data.results } });
    })();
  }, [eventId]);
  const fetchMilestones = React.useCallback(() => {
    (async () => {
      const milestones = await HTTPUtils.get<PaginationInfo<Milestone>>(Endpoints.MILESTONES(eventId));
      localDispatch({ type: 'replace', payload: { milestones: milestones.data.results } });
    })();
  }, [eventId]);
  const fetchAll = React.useCallback(() => {
    fetchRuns();
    fetchMilestones();
  }, [fetchMilestones, fetchRuns]);
  React.useEffect(() => {
    fetchAll();
    const interval = setInterval(fetchAll, 60000);
    return () => {
      clearInterval(interval);
    };
  }, [fetchAll]);
  const retry = React.useRef<number>(0);
  const [socket, setSocket] = React.useState<WebSocket | null>(null);
  const socketRef = React.useRef<WebSocket>();
  const connectWebsocket = React.useCallback(() => {
    const socket = new WebSocket(
      `${window.location.protocol.replace('http', 'ws')}//${window.location.host}/tracker/ws/donations/`,
    );

    socket.addEventListener('open', async () => {
      localDispatch({ type: 'replace', payload: { bids: [] } });
      if (eventId) {
        const bids = (await HTTPUtils.get<PaginationInfo<Bid>>(Endpoints.BIDS(eventId, feed, true))).data.results;
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
  }, [eventId, feed]);
  React.useEffect(() => {
    (async () => {
      const ago = DateTime.now().minus(Duration.fromObject({ hours: 3 })); // trigger only when run changes, not every minute
      const timestamps = [ago];
      if (currentRunStart) {
        timestamps.push(currentRunStart);
      }
      if (previousRunStart) {
        timestamps.push(previousRunStart);
      }
      const timestamp = DateTime.min(...timestamps);
      let pageInfo = (
        await HTTPUtils.get<PaginationInfo<Donation>>(Endpoints.DONATIONS(eventId), {
          time_gte: timestamp.toISO(),
        })
      ).data;
      const donations = pageInfo.results;
      while (pageInfo.next) {
        pageInfo = (await HTTPUtils.get<PaginationInfo<Donation>>(pageInfo.next)).data;
        donations.concat(pageInfo.results);
      }
      localDispatch({ type: 'replace', payload: { donations } });
    })();
    connectWebsocket();
  }, [APIV2_ROOT, connectWebsocket, currentRunStart, dispatch, eventId, previousRunStart]);

  const format = new Intl.NumberFormat([], { minimumFractionDigits: 2 });

  return (
    <>
      <div>
        Socket State: {socketState(socket)} {retry.current > 0 && `(${retry.current})`}
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
        <button onClick={connectWebsocket}>Force Refresh</button>
      </div>
      {total !== 0 && <h2>Total: ${format.format(total)}</h2>}
      {nextCheckpoint && (
        <h3>
          Next Checkpoint: <TimeSpan run={nextCheckpoint} /> ({iso(nextCheckpoint.endtime).toRelative()}){' '}
          {parseDuration(nextCheckpoint.setup_time).shiftTo('minutes').minutes} minute(s)
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
