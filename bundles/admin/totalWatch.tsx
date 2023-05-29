import * as React from 'react';
import moment, { Moment } from 'moment';
import { useSelector } from 'react-redux';
import { useParams } from 'react-router';

import { useConstants } from '@common/Constants';
import modelActions from '@public/api/actions/models';
import { paginatedFetch } from '@public/api/actions/paginate';
import { usePermission } from '@public/api/helpers/auth';
import useSafeDispatch from '@public/api/useDispatch';
import modelV2Actions, { BidFeed } from '@public/apiv2/actions/models';
import { Bid, BidChild, BidParent } from '@public/apiv2/Models';

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

type Donation = {
  pk: number;
  amount: number;
  timereceived: Moment;
};

type Speedrun = {
  pk: number;
  order: number | null;
  name: string;
  starttime: string;
  endtime: string;
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
  run: [number, number];
  intervals: { [k: number]: [number, number] };
};

export default React.memo(function TotalWatch() {
  const { event: eventId } = useParams<{ event: string }>();
  const event = useSelector((state: any) => state.models.event?.find((e: any) => e.pk === +eventId!));
  const runs = useSelector((state: any) => state.models.speedrun) as Speedrun[];
  // TODO: use the model state
  const { API_ROOT } = useConstants();
  const [feed, setFeed] = React.useState<BidFeed>('current');
  const hasHidden = usePermission('tracker.view_hidden_bid');
  const [apiDonations, setApiDonations] = React.useState<Donation[]>([]);
  const [feedDonations, setFeedDonations] = React.useState<Donation[]>([]);
  const currentRun = React.useMemo(() => runs?.find(r => moment().isBetween(r.starttime, r.endtime)), [runs]);
  const currentRunStart = React.useMemo(() => currentRun?.starttime, [currentRun]);
  const donations = React.useMemo(
    () => [...feedDonations, ...apiDonations.filter(ad => !feedDonations.some(fd => fd.pk === ad.pk))],
    [apiDonations, feedDonations],
  );
  const intervalData = React.useMemo(() => {
    const now = moment();
    return donations.reduce(
      (intervalData, donation) => {
        const timereceived = moment(donation.timereceived);
        if (currentRunStart && timereceived.isSameOrAfter(currentRunStart)) {
          intervalData.run[0] += 1;
          intervalData.run[1] += +donation.amount;
        }
        intervals.forEach(i => {
          if (timereceived.isSameOrAfter(now.clone().subtract(i, 'minutes'))) {
            const [c, t] = intervalData.intervals[i] || [0, 0];
            intervalData.intervals[i] = [c + 1, t + +donation.amount];
          }
        });
        return intervalData;
      },
      { run: [0, 0], intervals: {} } as IntervalData,
    );
  }, [currentRunStart, donations]);

  const [total, setTotal] = React.useState(0);
  React.useEffect(() => {
    if (event) {
      setTotal(event.amount);
    }
  }, [event]);
  const [bids, dispatchBids] = React.useReducer(bidsReducer, [] as Bid[]);
  const sortedBids = React.useMemo(() => {
    if (!bids) {
      return [];
    }
    return bids
      .filter(b => b.parent == null)
      .sort((a, b) => {
        const oa = runs?.find(r => a.speedrun === r.pk)?.order;
        const ob = runs?.find(r => b.speedrun === r.pk)?.order;
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
    dispatch(modelActions.loadModels('speedrun', { event: eventId }));
    const interval = setInterval(() => {
      dispatch(modelActions.loadModels('speedrun', { event: eventId }));
    }, 60000);
    return () => {
      clearInterval(interval);
    };
  }, [dispatch, eventId]);
  const retry = React.useRef<number>(0);
  const [socket, setSocket] = React.useState<WebSocket | null>(null);
  const connectWebsocket = React.useCallback(() => {
    const socket = new WebSocket(
      `${window.location.protocol.replace('http', 'ws')}//${window.location.host}/tracker/ws/donations/`,
    );

    socket.addEventListener('open', () => {
      dispatch(modelActions.loadModels('event', { id: eventId }));
      dispatchBids(null);
      dispatch(
        modelV2Actions.loadBids({
          eventId: +eventId,
          feed,
          tree: true,
        }),
      ).then(bids => dispatchBids(bids));
      retry.current = 0;
    });

    socket.addEventListener('error', err => {
      console.error(err);
      retry.current += 1;
    });

    socket.addEventListener('close', () => {
      const delay = Math.min(Math.pow(2.0, retry.current), 32);

      setTimeout(connectWebsocket, delay * 1000);
    });

    socket.addEventListener('message', ({ data }) => {
      data = JSON.parse(data);
      setTotal(data.new_total as number);
      dispatchBids(data.bids as Bid[]);
      setFeedDonations(donations =>
        donations
          .filter(d => d.pk !== data.id)
          .concat([
            {
              pk: data.id,
              amount: data.amount,
              timereceived: moment(data.timereceived),
            },
          ]),
      );
    });
    setSocket(socket);
  }, [dispatch, eventId, feed]);
  React.useEffect(() => {
    const ago = moment().subtract(3, 'hours');
    const timestamp = currentRunStart ? moment.min(moment(currentRunStart), ago) : ago;
    paginatedFetch(`${API_ROOT}search/?type=donation&event=${eventId}&time_gte=${timestamp.toISOString()}`).then(
      data => {
        setApiDonations(
          data.map((d: any) => ({ pk: d.pk, amount: d.fields.amount, timereceived: moment(d.fields.timereceived) })),
        );
      },
    );
    connectWebsocket();
  }, [API_ROOT, connectWebsocket, currentRunStart, dispatch, eventId]);

  const format = new Intl.NumberFormat([], { minimumFractionDigits: 2 });

  return (
    <>
      <div>
        Socket State: {socketState(socket)} {retry.current > 0 && `(${retry.current})`}
      </div>
      <div>
        <label>
          <select onChange={e => setFeed(e.target.value as BidFeed)}>
            <option value="current" selected={feed === 'current'}>
              Current
            </option>
            <option value="public" selected={feed === 'public'}>
              {hasHidden ? 'Public' : 'All'}
            </option>
            {hasHidden && (
              <option value="all" selected={feed === 'all'}>
                All
              </option>
            )}
          </select>{' '}
          Bid Feed
        </label>
      </div>
      <div>
        <button onClick={connectWebsocket}>Force Refresh</button>
      </div>
      {total && <h2>Total: ${format.format(total)}</h2>}
      {currentRun && (
        <>
          <h3>Current Run: {currentRun.name}</h3>
          <h4>
            Total since run start: ${format.format(intervalData.run[1])} ({intervalData.run[0]})
          </h4>
        </>
      )}
      {Object.entries(intervalData.intervals).map(([k, v]) => (
        <h4 key={k}>
          Total in the last {k} minutes: ${format.format(v[1])} ({v[0]})
        </h4>
      ))}
      {sortedBids?.map(bid => {
        const speedrun = runs?.find(r => bid.speedrun === r.pk);
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
                {speedrun && `${speedrun.name} -- `}
                {bid.name} ${format.format(bid.total)}
                {`/$${format.format(+bid.chain_goal + +bid.chain_remaining)}`} ({bid.state})
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
            </React.Fragment>
          );
        } else {
          return (
            <React.Fragment key={bid.id}>
              <h3>
                {speedrun && `${speedrun.name} -- `}
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
            </React.Fragment>
          );
        }
      })}
    </>
  );
});
