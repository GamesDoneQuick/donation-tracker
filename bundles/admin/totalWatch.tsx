import * as React from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useParams } from 'react-router';

import modelActions from '../public/api/actions/models';
import moment from 'moment';

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
  speedrun__name?: string;
  speedrun__order?: number;
  state: string;
};

function bidsReducer(state: Bid[], action: Bid[]) {
  return action.reduce((bids, bid) => bids.filter(b => b.pk !== bid.pk).concat([bid]), state);
}

export default React.memo(function TotalWatch() {
  const { event: eventId } = useParams();
  const event = useSelector((state: any) => state.models.event?.find((e: any) => e.pk === +eventId!));
  const currentRun = useSelector((state: any) =>
    state.models.speedrun?.find((r: any) => moment().isBetween(r.starttime, r.endtime)),
  );

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
        if (a.speedrun__order && !b.speedrun__order) {
          return 1;
        } else if (b.speedrun__order && !a.speedrun__order) {
          return -1;
        } else if (a.speedrun__order && b.speedrun__order) {
          return a.speedrun__order - b.speedrun__order;
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
  }, [bids]);
  const dispatch = useDispatch();
  React.useEffect(() => {
    dispatch(modelActions.loadModels('speedrun', { event: eventId }));
    const interval = setInterval(() => {
      dispatch(modelActions.loadModels('speedrun', { event: eventId }));
    }, 60000);
    return () => {
      clearInterval(interval);
    };
  }, [dispatch, eventId]);
  React.useEffect(() => {
    if (currentRun) {
      dispatch(modelActions.loadModels('allbids', { run: currentRun.pk }));
    }
  }, [currentRun?.pk, dispatch]);
  const retry = React.useRef<number>(0);
  const [socket, setSocket] = React.useState<WebSocket | null>(null);
  const connectWebsocket = React.useCallback(() => {
    const socket = new WebSocket(
      `${window.location.protocol.replace('http', 'ws')}//${window.location.host}/tracker/ws/donations/`,
    );

    socket.addEventListener('open', () => {
      dispatch(modelActions.loadModels('event', { id: eventId }));
      dispatch(modelActions.loadModels('allbids', { event: eventId, feed: 'open' }));
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
      {currentRun && <h3>Current Run: {currentRun.name}</h3>}
      {sortedBids?.map(bid =>
        bid.parent ? (
          <h4 key={bid.pk}>
            {bid.name} ${format.format(bid.total)}{' '}
          </h4>
        ) : (
          <h3 key={bid.pk}>
            {bid.speedrun__name && `${bid.speedrun__name} -- `}
            {bid.name} ${format.format(bid.total)}
            {bid.goal ? `/$${format.format(bid.goal)}` : null} ({bid.state})
          </h3>
        ),
      )}
    </>
  );
});
