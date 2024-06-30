import * as React from 'react';
import { DateTime, Duration, Interval } from 'luxon';
import { useSelector } from 'react-redux';
import { useParams } from 'react-router';

import { useConstants } from '@common/Constants';
import { paginatedFetch } from '@public/api/actions/paginate';
import { usePermission } from '@public/api/helpers/auth';
import useSafeDispatch from '@public/api/useDispatch';
import modelV2Actions, { BidFeed } from '@public/apiv2/actions/models';
import { Bid, BidChild, BidParent, Run } from '@public/apiv2/Models';

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

// TODO: move this to V2

type Event = {
  id: number;
  amount: number;
};

type Donation = {
  id: number;
  amount: number;
  timereceived: DateTime;
};

function bidsReducer(state: Bid[], action: Bid[] | null) {
  if (action == null) {
    return [];
  }
  state = action
    .filter(bid => bid.parent == null)
    .reduce((bids, bid) => bids.filter(b => b.id !== bid.id).concat([bid]), state);
  action
    .filter(bid => bid.parent != null)
    .forEach(bid => {
      const parentIndex = state.findIndex(parent => parent.id === bid.parent);
      if (parentIndex >= 0) {
        const parent = state[parentIndex] as BidParent;
        const option = parent.options.findIndex(option => option.id === bid.id);
        const newParent = { ...parent };
        if (option >= 0) {
          newParent.options = [...newParent.options];
          newParent.options[option] = { ...newParent.options[option], total: bid.total };
        } else {
          newParent.options = [...newParent.options, bid as BidChild];
        }
        state.splice(parentIndex, 1, {
          ...newParent,
          total: newParent.options.reduce((total, option) => total + +option.total, 0),
        });
      }
    });
  return state;
}

const intervals = [5, 15, 30, 60, 180];

type IntervalData = {
  // count, amount
  previous: [number, number];
  current: [number, number];
  intervals: { [k: number]: [number, number] };
};

function starts(time: DateTime) {
  return `start${time < DateTime.now() ? 'ed' : 's'} ${time.toRelative()}`;
}

function TimeSpan({ run }: { run: Run }) {
  return (
    <>
      {run.starttime.toFormat('cccc h:mm a')}-{run.endtime.toFormat('h:mm a')}
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
function useTimestamp(timestamp: DateTime | number | undefined) {
  if (timestamp instanceof DateTime) {
    timestamp = timestamp.toMillis();
  }
  return React.useMemo(() => timestamp && DateTime.fromMillis(timestamp as number), [timestamp]);
}

interface State {
  models: {
    event?: Event[];
    run?: Run[];
  };
}

export default React.memo(function TotalWatch() {
  const now = useNow();
  const { event: eventId } = useParams<{ event: string }>();
  const event = useSelector<State, Event | undefined>(state => state.models.event?.find(e => e.id === +eventId!));
  const runs = useSelector<State, Run[]>(state => state.models.run?.filter(run => run.event === +eventId!) || []);
  // TODO: use the model state
  const { API_ROOT } = useConstants();
  const [feed, setFeed] = React.useState<BidFeed>('current');
  const hasHidden = usePermission('tracker.view_hidden_bid');
  const [apiDonations, setApiDonations] = React.useState<Donation[]>([]);
  const [feedDonations, setFeedDonations] = React.useState<Donation[]>([]);
  const currentRun = React.useMemo(
    () => runs?.find(r => Interval.fromDateTimes(r.starttime, r.endtime).contains(now)),
    [now, runs],
  );
  const currentRunStart = useTimestamp(currentRun?.starttime);
  const previousRun = React.useMemo(() => runs?.filter(r => now > r.endtime).slice(-1)?.[0], [now, runs]);
  const previousRunStart = useTimestamp(previousRun?.starttime);
  const nextCheckpoint = React.useMemo(() => {
    const nextAnchor = runs?.find(r => r.anchor_time != null && r.order != null && now < r.anchor_time);
    if (nextAnchor) {
      return runs?.find(r => r.order === nextAnchor.order! - 1);
    }
  }, [now, runs]);
  const donations = React.useMemo(
    () => [...feedDonations, ...apiDonations.filter(ad => !feedDonations.some(fd => fd.id === ad.id))],
    [apiDonations, feedDonations],
  );
  const intervalData = React.useMemo(() => {
    return donations.reduce(
      (intervalData, donation) => {
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
          if (donation.timereceived >= now.minus(Duration.fromObject({ minutes: i }))) {
            const [c, t] = intervalData.intervals[i] || [0, 0];
            intervalData.intervals[i] = [c + 1, t + +donation.amount];
          }
        });
        return intervalData;
      },
      { previous: [0, 0], current: [0, 0], intervals: {} } as IntervalData,
    );
  }, [currentRunStart, donations, now, previousRunStart]);

  const [total, setTotal] = React.useState(0);
  React.useEffect(() => {
    if (event) {
      setTotal(event.amount);
    }
  }, [event]);
  const [bids, dispatchBids] = React.useReducer(bidsReducer, [] as Bid[]);
  const sortedBids = React.useMemo(() => {
    if (!bids?.length) {
      return [];
    }
    return bids
      .filter(b => b.parent == null)
      .sort((a, b) => {
        const oa = runs?.find(r => a.speedrun === r.id)?.order;
        const ob = runs?.find(r => b.speedrun === r.id)?.order;
        if (oa && ob == null) {
          return 1;
        } else if (ob && oa == null) {
          return -1;
        } else if (oa && ob) {
          return oa - ob;
        } else {
          return a.name.localeCompare(b.name);
        }
      })
      .reduce((memo, parent) => {
        const chain = parent.istarget && parent.chain && parent.parent == null;
        const options = !parent.istarget && !parent.chain;
        if (chain) {
          return memo.concat([
            parent,
            ...(parent.chain_steps.map(step => ({
              ...step,
              chain: true,
              parent: parent.id,
            })) as Bid[]),
          ]);
        } else if (options) {
          return memo.concat([
            parent,
            ...parent.options
              .map(child => ({ ...child, parent: parent.id }))
              .sort((a, b) => {
                return b.total - a.total || a.name.localeCompare(b.name);
              }),
          ]);
        } else {
          return memo.concat([parent]);
        }
      }, [] as Bid[]);
  }, [bids, runs]);
  const dispatch = useSafeDispatch();
  React.useEffect(() => {
    dispatch(modelV2Actions.loadRuns({ eventId: +eventId! }));
    const interval = setInterval(() => {
      dispatch(modelV2Actions.loadRuns({ eventId: +eventId! }));
    }, 60000);
    return () => {
      clearInterval(interval);
    };
  }, [dispatch, eventId]);
  const retry = React.useRef<number>(0);
  const [socket, setSocket] = React.useState<WebSocket | null>(null);
  const socketRef = React.useRef<WebSocket>();
  const connectWebsocket = React.useCallback(() => {
    const socket = new WebSocket(
      `${window.location.protocol.replace('http', 'ws')}//${window.location.host}/tracker/ws/donations/`,
    );

    socket.addEventListener('open', () => {
      dispatchBids(null);
      dispatch(
        modelV2Actions.loadBids({
          eventId: +eventId,
          feed: feed === 'open' ? 'current' : feed,
          tree: true,
        }),
      ).then(bids => {
        dispatchBids(bids);
        if (feed === 'open') {
          dispatch(
            modelV2Actions.loadBids({
              eventId: +eventId,
              feed,
              tree: true,
            }),
          ).then(bids => dispatchBids(bids));
        }
      });
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
      dispatchBids(parsedData.bids as Bid[]);
      const donation: Donation = {
        id: parsedData.id,
        amount: parsedData.amount,
        timereceived: DateTime.fromISO(parsedData.timereceived),
      };
      setFeedDonations(donations => donations.filter(d => d.id !== data.id).concat([donation]));
    });
    setSocket(oldSocket => {
      socketRef.current = socket;
      if (oldSocket) {
        oldSocket.close();
      }
      return socket;
    });
  }, [dispatch, eventId, feed]);
  React.useEffect(() => {
    const ago = DateTime.now().minus(Duration.fromObject({ hours: 3 })); // trigger only when run changes, not every minute
    const timestamps = [ago];
    if (currentRunStart) {
      timestamps.push(currentRunStart);
    }
    if (previousRunStart) {
      timestamps.push(previousRunStart);
    }
    const timestamp = DateTime.min(...timestamps);
    paginatedFetch(
      `${API_ROOT}search/`,
      new URLSearchParams({ type: 'donation', event: `${eventId}`, time_gte: timestamp.toISO()! }),
    ).then(data => {
      setApiDonations(
        data.map((d: any) => ({
          id: d.pk,
          amount: d.fields.amount,
          timereceived: DateTime.fromISO(d.fields.timereceived),
        })),
      );
    });
    connectWebsocket();
  }, [API_ROOT, connectWebsocket, currentRunStart, dispatch, eventId, previousRunStart]);

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
            <option value="public">{hasHidden ? 'Public' : 'All'}</option>
            {hasHidden && <option value="all">All</option>}
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
      {sortedBids?.map(bid => {
        const speedrun = runs?.find(r => bid.speedrun === r.id);
        if (bid.parent) {
          if (bid.chain) {
            return (
              <h4 key={bid.id}>
                {bid.name} ${format.format(bid.total)}/${format.format(bid.goal)}
              </h4>
            );
          } else {
            return (
              <h4 key={bid.id}>
                {bid.name} ${format.format(bid.total)}
              </h4>
            );
          }
        } else if (bid.chain && bid.parent == null) {
          return (
            <React.Fragment key={bid.id}>
              <h3>
                {speedrun && `${speedrun.name} (${starts(speedrun.starttime)}) -- `}
                {bid.name} ${format.format(bid.total)}
                {`/$${format.format(+bid.chain_goal + +bid.chain_remaining)}`} ({bid.state}){bid.pinned && ' 📌'}
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
            </React.Fragment>
          );
        } else {
          return (
            <React.Fragment key={bid.id}>
              <h3>
                {speedrun && `${speedrun.name} (${starts(speedrun.starttime)}) -- `}
                {bid.name} ${format.format(bid.total)}
                {bid.goal ? `/$${format.format(bid.goal)}` : ''} ({bid.state}){bid.pinned && ' 📌'}
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
            </React.Fragment>
          );
        }
      })}
    </>
  );
});
