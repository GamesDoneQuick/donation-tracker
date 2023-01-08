import * as React from 'react';
import moment, { Moment } from 'moment';
import { useDispatch, useSelector } from 'react-redux';
import { useParams } from 'react-router';

import { useConstants } from '@common/Constants';
import { paginatedFetch } from '@public/api/actions/paginate';

import modelActions from '../public/api/actions/models';

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

type Bid = {
  pk: number;
  total: number;
  parent: number | null;
  name: string;
  goal: number;
  speedrun?: number;
  state: string;
};

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

function bidsReducer(state: Bid[], action: Bid[]) {
  return action.reduce((bids, bid) => bids.filter(b => b.pk !== bid.pk).concat([bid]), state);
}

const intervals = [5, 15, 30, 60, 180];

type IntervalData = {
  run: number;
  intervals: { [k: number]: number };
};

export default React.memo(function TotalWatch() {
  const { event: eventId } = useParams<{ event: string }>();
  const event = useSelector((state: any) => state.models.event?.find((e: any) => e.pk === +eventId!));
  const runs = useSelector((state: any) => state.models.speedrun) as Speedrun[];
  // TODO: use the model state
  const { API_ROOT } = useConstants();
  const [apiDonations, setApiDonations] = React.useState<Donation[]>([]);
  const [feedDonations, setFeedDonations] = React.useState<Donation[]>([]);
  const currentRun = React.useMemo(() => runs?.find(r => moment().isBetween(r.starttime, r.endtime)), [runs]);
  const donations = React.useMemo(
    () => [...feedDonations, ...apiDonations.filter(ad => !feedDonations.some(fd => fd.pk === ad.pk))],
    [apiDonations, feedDonations],
  );
  const intervalData = React.useMemo(() => {
    const now = moment();
    return donations.reduce(
      (intervalData, donation) => {
        const timereceived = moment(donation.timereceived);
        if (currentRun && timereceived.isSameOrAfter(currentRun.starttime)) {
          intervalData.run += +donation.amount;
        }
        intervals.forEach(i => {
          if (timereceived.isSameOrAfter(now.clone().subtract(i, 'minutes'))) {
            intervalData.intervals[i] = (intervalData.intervals[i] || 0) + +donation.amount;
          }
        });
        return intervalData;
      },
      { run: 0, intervals: {} } as IntervalData,
    );
  }, [currentRun, donations]);

  const [total, setTotal] = React.useState(0);
  React.useEffect(() => {
    if (event) {
      setTotal(event.amount);
    }
  }, [event]);
  const bidsFromServer = useSelector((state: any) => state.models.bid) as Bid[];
  const [bids, dispatchBids] = React.useReducer(bidsReducer, [] as Bid[]);
  React.useEffect(() => {
    if (bidsFromServer) {
      dispatchBids(bidsFromServer as Bid[]);
    }
  }, [bidsFromServer]);
  const sortedBids = React.useMemo(() => {
    if (!bids) {
      return [];
    }
    return bids
      .filter(b => !b.parent)
      .sort((a, b) => {
        const oa = runs?.find(r => a.speedrun === r.pk)?.order;
        const ob = runs?.find(r => b.speedrun === r.pk)?.order;
        if (oa && !ob) {
          return 1;
        } else if (ob && !oa) {
          return -1;
        } else if (oa && ob) {
          return oa - ob;
        } else {
          return a.name.localeCompare(b.name);
        }
      })
      .reduce((memo, parent) => {
        const children = bids
          .filter(b => b.parent === parent.pk)
          .sort((a, b) => {
            return b.total - a.total || a.name.localeCompare(b.name);
          });
        return memo.concat([parent, ...children]);
      }, [] as Bid[]);
  }, [bids, runs]);
  const dispatch = useDispatch();
  React.useEffect(() => {
    const ago = moment().subtract(3, 'hours');
    const timestamp = currentRun ? moment.min(moment(currentRun.starttime), ago) : ago;
    paginatedFetch(`${API_ROOT}search/?type=donation&time_gte=${timestamp.toISOString()}`).then(data => {
      setApiDonations(
        data.map((d: any) => ({ pk: d.pk, amount: d.fields.amount, timereceived: moment(d.fields.timereceived) })),
      );
    });
  }, [API_ROOT, currentRun, dispatch, eventId]);
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
      dispatch(modelActions.loadModels('allbids', { event: eventId, feed: 'current_plus' }));
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
  }, [dispatch, eventId]);
  React.useEffect(() => {
    connectWebsocket();
  }, [connectWebsocket]);

  const format = new Intl.NumberFormat();

  return (
    <>
      <div>
        Socket State: {socketState(socket)} {retry.current > 0 && `(${retry.current})`}
      </div>
      {total && <h2>Total: ${format.format(total)}</h2>}
      {currentRun && (
        <>
          <h3>Current Run: {currentRun.name}</h3>
          <h4>Total since run start: ${format.format(intervalData.run)}</h4>
        </>
      )}
      {Object.entries(intervalData.intervals).map(([k, v]) => (
        <h4 key={k}>
          Total in the last {k} minutes: ${format.format(v)}
        </h4>
      ))}
      {sortedBids?.map(bid => {
        const speedrun = runs?.find(r => bid.speedrun === r.pk);
        return bid.parent ? (
          <h4 key={bid.pk}>
            {bid.name} ${format.format(bid.total)}{' '}
          </h4>
        ) : (
          <h3 key={bid.pk}>
            {speedrun && `${speedrun.name} -- `}
            {bid.name} ${format.format(bid.total)}
            {bid.goal ? `/$${format.format(bid.goal)}` : null} ({bid.state})
          </h3>
        );
      })}
    </>
  );
});
